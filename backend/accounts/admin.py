from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import *
from django.db import transaction
from django.utils import timezone




class AccountAdmin(UserAdmin):
    list_display = ('display_avatar', 'username', 'email', 'id', 'is_active')
    list_display_links = ('display_avatar', 'username')
    search_fields = ('username', 'email', 'id')
    readonly_fields = ('id', 'last_login', 'date_joined')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('image', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
        ('System IDs', {'fields': ('id',)}),
    )

    def display_avatar(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 35px; height: 35px; border-radius: 50%;" />', obj.image.url)
        return "No Image"
    display_avatar.short_description = "Avatar"

admin.site.register(Account, AccountAdmin)

admin.site.register(UserProfile)
admin.site.register(PlayerGameID)
admin.site.register(WalletTransaction)




@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'upi_id', 'status', 'created_at', 'processed_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'upi_id']
    readonly_fields = ['created_at', 'processed_at']
    
    actions = ['approve_requests', 'reject_and_refund_requests']

    # --- THIS IS THE NEW MAGIC ---
    def save_model(self, request, obj, form, change):
        if change: # If we are editing an EXISTING request
            # Get the original object from the database BEFORE we save the new changes
            old_obj = WithdrawalRequest.objects.get(pk=obj.pk)
            
            # Did the admin change the dropdown from PENDING to REJECTED?
            if old_obj.status == 'PENDING' and obj.status == 'REJECTED':
                with transaction.atomic():
                    obj.processed_at = timezone.now()
                    if not obj.admin_note:
                        obj.admin_note = "Rejected by admin. Funds have been returned to your wallet."
                    
                    # Refund the wallet
                    profile = UserProfile.objects.select_for_update().get(user=obj.user)
                    profile.wallet_balance += obj.amount
                    profile.save()

                    # Create Ledger Entry
                    WalletTransaction.objects.create(
                        user=obj.user,
                        amount=obj.amount,
                        transaction_type='WITHDRAWAL_REJECTED',
                        description=f"Refunded: Withdrawal to {obj.upi_id} was rejected",
                        withdrawal_request=obj
                    )
            
            # Did the admin change the dropdown from PENDING to COMPLETED?
            elif old_obj.status == 'PENDING' and obj.status == 'COMPLETED':
                obj.processed_at = timezone.now()

        # Finally, save the object to the database
        super().save_model(request, obj, form, change)
    # -----------------------------

    @admin.action(description='✅ APPROVE: Mark as Completed (Do this AFTER paying them)')
    def approve_requests(self, request, queryset):
        # ... (Keep your existing action code here) ...
        pending_requests = queryset.filter(status='PENDING')
        updated_count = pending_requests.update(status='COMPLETED', processed_at=timezone.now())
        self.message_user(request, f"Successfully marked {updated_count} requests as COMPLETED.")

    @admin.action(description='❌ REJECT: Cancel Request & Refund Wallet')
    def reject_and_refund_requests(self, request, queryset):
        # ... (Keep your existing action code here) ...
        rejected_count = 0
        pending_requests = queryset.filter(status='PENDING')

        for req in pending_requests:
            with transaction.atomic():
                req.status = 'REJECTED'
                req.processed_at = timezone.now()
                if not req.admin_note:
                    req.admin_note = "Rejected by admin. Funds have been returned to your wallet."
                req.save()

                profile = UserProfile.objects.select_for_update().get(user=req.user)
                profile.wallet_balance += req.amount
                profile.save()

                WalletTransaction.objects.create(
                    user=req.user,
                    amount=req.amount,
                    transaction_type='WITHDRAWAL_REJECTED',
                    description=f"Refunded: Withdrawal to {req.upi_id} was rejected",
                    withdrawal_request=req
                )
                rejected_count += 1

        self.message_user(request, f"Successfully REJECTED {rejected_count} requests and refunded the users' wallets.")