from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import Account

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