from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated,AllowAny
from django.db import transaction
from django.shortcuts import get_object_or_404
from decimal import Decimal, InvalidOperation

from .models import UserProfile, WalletTransaction, WithdrawalRequest


class RequestWithdrawalView(APIView):
    permission_classes = [IsAuthenticated]


    @transaction.atomic
    def post(self, request):
        amount = request.data.get('amount')
        upi_id = request.data.get('upi_id')

        if not amount or not upi_id:
            return Response({'error': 'Amount and UPI ID are required'}, status= status.HTTP_400_BAD_REQUEST)
        
        try:
            amount = Decimal(amount)
            if amount <= 0:
                return Response({'error': 'Amount should be greater than zero'}, status= status.HTTP_400_BAD_REQUEST)
        except InvalidOperation:
            return Response({'error': 'Invalid amount format'}, status= status.HTTP_400_BAD_REQUEST)
        
        # Now lock the profile to prvent race conditions
        profile = get_object_or_404(UserProfile.objects.select_for_update(), user = request.user)

        # check do the user have enough wallet balance
        if profile.wallet_balance < amount:
            return Response({'error': 'Insufficient wallet balance'}, status= status.HTTP_400_BAD_REQUEST)
        

        # if everything ok, then deduct the balance immediately
        profile.wallet_balance -= amount
        profile.save()

        # Create our ledger entry
        WalletTransaction.objects.create(
            user = request.user,
            amount = amount,
            transaction_type = 'WITHDRAWAL_PENDING',
            description = f"Withdrawal request to UPI ID:{upi_id}"
        )

        # Create a withdrawalRequest entry so that the admin can see it 
        WithdrawalRequest.objects.create(
            user = request.user,
            amount = amount,
            upi_id = upi_id
        )

        return Response({
            'message': 'Withdrawal request submitted successfully, will be be processed within 24 hours',
            'new_balance' : profile.wallet_balance,
        }, status= status.HTTP_201_CREATED)

