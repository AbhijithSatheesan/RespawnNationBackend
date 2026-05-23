from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser

# Create your models here.

class Account(AbstractUser):
    email = models.EmailField(max_length=50, unique= True)
    image = models.ImageField(blank= True, null= True)
    
    # To make login via email
    USERNAME_FIELD = 'email'

    # To make username field still mandatory even if we are not using it for login
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.username









class UserProfile(models.Model):
    # 1. Identity & Link
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(max_length=500, blank=True, null=True)
    banner_image = models.ImageField(upload_to='profiles/banners/', blank=True, null=True)
    
    # 2. Social Connections
    discord_username = models.CharField(max_length=100, blank=True, null=True)
    youtube_link = models.URLField(blank=True, null=True)
    twitter_link = models.URLField(blank=True, null=True)
    # Note: Twitch is already handled by your Stream model!
    
    # 3. The Wallet (Current State)
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.user.username}'s Profile"


class PlayerGameID(models.Model):
    """
    The 'ID Vault'. Saves their specific username for specific games 
    (e.g., Valorant Riot ID, BGMI Character ID) so they don't type it every time.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_game_ids')
    game = models.ForeignKey('games.Games', on_delete=models.CASCADE)
    in_game_id = models.CharField(max_length=100, help_text="e.g., Faker#NA1, 5123456789")

    class Meta:
        # A user can only have ONE saved ID per game
        unique_together = ('user', 'game')

    def __str__(self):
        return f"{self.user.username} - {self.game.name}: {self.in_game_id}"


class WalletTransaction(models.Model):
    """
    The Financial Ledger. NEVER update wallet_balance without creating one of these.
    """
    TRANSACTION_TYPES = [
        ('DEPOSIT', 'Added Funds'),
        ('WITHDRAWAL', 'Cashed Out'),
        ('WITHDRAWAL_PENDING', 'Withdrawal Requested'),
        ('WITHDRAWAL_REJECTED', 'Withdrawal Refunded'),
        ('ENTRY_FEE', 'Tournament Entry Fee'),
        ('PRIZE', 'Prize Money Won'),
        ('REFUND', 'Tournament Refund')
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    description = models.CharField(max_length=255, help_text="e.g., 'Won 1st Place in BGMI Weekly'")
    
    # Optional link to the tournament (if it was an entry fee or prize)
    tournament = models.ForeignKey('tournaments.Tournament', on_delete=models.SET_NULL, null=True, blank=True)

    # Link to Withdrawal request
    withdrawal_request = models.ForeignKey('WithdrawalRequest', on_delete=models.SET_NULL, null= True, blank= True, related_name='ledger_entries')
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        sign = "+" if self.transaction_type in ['DEPOSIT', 'PRIZE', 'REFUND'] else "-"
        return f"{self.user.username} | {self.get_transaction_type_display()} | {sign}₹{self.amount}"
    



# <-----------  Model to track deposits to wallet added through razorpay  ------------------>

class WalletDepositOrder(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete= models.CASCADE, related_name= 'deposit_orders')
    razorpay_order_id = models.CharField(max_length= 255, unique= True)
    amount = models.DecimalField(max_digits= 10, decimal_places= 2, help_text= 'amount in INR')
    is_paid = models.BooleanField(default= False)
    created_at = models.DateTimeField(auto_now_add= True)

    def __str__(self):
        return f"{self.user.username}'s Deposit of ₹{self.amount} -paid {self.is_paid}"





#  <---------  Withdraw money -------------->

class WithdrawalRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('COMPLETED', 'Completed'),
        ('REJECTED', 'Rejected / Refunded'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete= models.CASCADE, related_name='withdrawals')
    amount = models.DecimalField(max_digits= 10, decimal_places= 2)
    upi_id = models.CharField(max_length= 100, help_text="User's upi id for cash transfer")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default= "PENDING")

    # If admin wants to give a message back
    admin_note = models.TextField(blank= True, null= True)

    created_at = models.DateTimeField(auto_now_add= True)
    processed_at = models.DateTimeField(blank= True, null= True)

    def __str__(self):
        return f"{self.user.username} - ₹{self.amount} ({self.status})"

        