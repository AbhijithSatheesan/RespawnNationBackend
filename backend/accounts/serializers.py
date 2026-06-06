from rest_framework import serializers
from .models import UserProfile, WalletTransaction

from djoser.serializers import UserSerializer as BaseUserSerializer
from .models import Account




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
            'username', 'email', 'bio','profile_picture', 'banner_image', 
            'discord_username', 'wallet_balance', 'total_earnings',
            'recent_transactions'
        ]

    def get_recent_transactions(self, obj):
        # Fetch only the 5 most recent transactions for the dashboard
        transactions = obj.user.transactions.all()[:5]
        return WalletTransactionSerializer(transactions, many=True).data
    



# Edit the djoser serializer to send profile picture from user profile when loggin in


class CustomUserSerializer(BaseUserSerializer):
    # Add a custom field that doesn't exist on the Account model directly
    profile_picture = serializers.SerializerMethodField()

    class Meta(BaseUserSerializer.Meta):
        model = Account
        # Add profile_picture to the fields Djoser returns
        fields = ['id', 'email', 'username', 'profile_picture'] 

    def get_profile_picture(self, obj):
        # Safely check if the user has a profile and an image
        if hasattr(obj, 'profile') and obj.profile.profile_picture:
            request = self.context.get('request')
            url = obj.profile.profile_picture.url
            
            # If using Cloudinary, it might already be a full URL
            if 'http' in url:
                return url
            # If local, build the full URL
            if request:
                return request.build_absolute_uri(url)
            return url
        return None