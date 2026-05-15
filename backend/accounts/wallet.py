import razorpay
import uuid
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated,AllowAny
from django.db import transaction
from django.shortcuts import get_object_or_404
from decimal import Decimal, InvalidOperation


from .models import UserProfile, WalletTransaction, WithdrawalRequest, WalletDepositOrder


razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


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

        # Create a withdrawalRequest entry so that the admin can see it 
        withdrawal_req = WithdrawalRequest.objects.create(
            user = request.user,
            amount = amount,
            upi_id = upi_id
        )

        # Create our ledger entry
        WalletTransaction.objects.create(
            user = request.user,
            amount = amount,
            transaction_type = 'WITHDRAWAL_PENDING',
            description = f"Withdrawal request to UPI ID:{upi_id}",
            withdrawal_request = withdrawal_req

        )

       

        return Response({
            'message': 'Withdrawal request submitted successfully, will be be processed within 24 hours',
            'new_balance' : profile.wallet_balance,
        }, status= status.HTTP_201_CREATED)






# First we should generate deposit order
class GenerateDepositOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        amount = request.data.get('amount')


        if not amount:
            return Response({'error': 'Amount is required'}, status= status.HTTP_400_BAD_REQUEST)
        
        try:
            amount_in_inr = Decimal(amount)
            if amount_in_inr <= 0:
                return Response({'error': 'Amount should be greater than zero'}, status= status.HTTP_400_BAD_REQUEST)
        except InvalidOperation:
            return Response({'error':'Invalid amount format'}, status= status.HTTP_400_BAD_REQUEST)
        
        amount_in_paise = int(amount_in_inr * 100)
        unique_receipt = f"wallet_topup_user{request.user.id}_{uuid.uuid4().hex[:6]}"

        try:
            # create a razorpay order
            razorpay_order = razorpay_client.order.create({
                'amount':amount_in_paise,
                'currency': 'INR',
                'receipt' : unique_receipt,
                'payment_capture' : 1
            })

            # save it to database
            WalletDepositOrder.objects.create(
                user = request.user,
                razorpay_order_id = razorpay_order['id'],
                amount = amount_in_inr
            )

            # send id back t o react so that it can open checkout window
            return Response({
                'order_id': razorpay_order['id'],
                'amount' : amount_in_paise,
                'currency' : 'INR'
            }, status= status.HTTP_200_OK)
        
        except Exception as e:
            return Response({'error': str(e)}, status= status.HTTP_500_INTERNAL_SERVER_ERROR)

        



# verify and add funds

class VerifyDepositView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_order_id = request.data.get('razorpay_order_id')
        razorpay_signature = request.data.get('razorpay_signature')

        if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
            return Response({'error': 'Missing payment data'}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Verify Signature cryptographically
        try:
            razorpay_client.utility.verify_payment_signature({
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_order_id': razorpay_order_id,
                'razorpay_signature': razorpay_signature
            })
        except razorpay.errors.SignatureVerificationError:
            return Response({'error': 'Invalid Payment Signature'}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Database Order Validation
        try:
            db_order = WalletDepositOrder.objects.get(razorpay_order_id=razorpay_order_id)

            if db_order.user != request.user:
                return Response({'error': 'Cross Payment tampering detected'}, status=status.HTTP_403_FORBIDDEN)
            
            if db_order.is_paid:
                return Response({'error': 'This order has already been processed'}, status=status.HTTP_400_BAD_REQUEST)
        except WalletDepositOrder.DoesNotExist:
            return Response({'error': 'Order not found in our records'}, status=status.HTTP_404_NOT_FOUND)

        # 3. Double check with Razorpay that money was actually captured
        try:
            payment_details = razorpay_client.payment.fetch(razorpay_payment_id)
            if payment_details['status'] != 'captured':
                return Response({'error': 'Payment has not been captured by bank'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({'error': 'Could not verify payment details with Razorpay'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 4. Success! Lock the profile and add the money
        profile = get_object_or_404(UserProfile.objects.select_for_update(), user=request.user)
        profile.wallet_balance += db_order.amount
        profile.save()

        # Mark order as paid
        db_order.is_paid = True
        db_order.save()

        # Create Ledger Entry
        WalletTransaction.objects.create(
            user=request.user,
            amount=db_order.amount,
            transaction_type='DEPOSIT',
            description=f"Added funds via Razorpay"
        )

        return Response({
            'message': f'Successfully deposited ₹{db_order.amount} to your wallet!',
            'new_balance': profile.wallet_balance
        }, status=status.HTTP_200_OK)