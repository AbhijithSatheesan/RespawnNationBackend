from rest_framework import serializers
from .models import UserProfile, WalletTransaction

class WalletTransactionSerializer(serializers.ModelSerializer):
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)

    class Meta:
        model = WalletTransaction
        fields = ['id', 'amount', 'transaction_type', 'transaction_type_display', 'description', 'created_at']

class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    # Bring in the last 5 transactions nested inside the profile!
    recent_transactions = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            'username', 'email', 'bio', 'banner_image', 
            'discord_username', 'wallet_balance', 'total_earnings',
            'recent_transactions'
        ]

    def get_recent_transactions(self, obj):
        # Fetch only the 5 most recent transactions for the dashboard
        transactions = obj.user.transactions.all()[:5]
        return WalletTransactionSerializer(transactions, many=True).data