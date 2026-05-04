import razorpay
from django.conf import settings
import uuid
from django.db import transaction, IntegrityError
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view,permission_classes
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from decimal import Decimal
from .models import Tournament,Participant,Order
from .serializers import TournamentSerializer, TournamentDetailSerializer

# 1. Create a custom Pagination class for your Tournaments
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 2 # Fetch 10 at a time
    page_size_query_param = 'page_size'
    max_page_size = 50

class TournamentListView(generics.ListAPIView):
    serializer_class = TournamentSerializer
    pagination_class = StandardResultsSetPagination # 2. Tell the view to use it

    def get_queryset(self):
        queryset = Tournament.objects.all()
        requested_status = self.request.query_params.get('status', None)

        if requested_status:
            queryset = queryset.filter(status=requested_status)

        # 3. Just order them, the pagination class will handle the slicing automatically!
        return queryset.order_by('registration_deadline')
    

class TournamentDetailView(generics.RetrieveAPIView):
    queryset = Tournament.objects.all()
    serializer_class = TournamentDetailSerializer
    lookup_field = 'id' # This tells Django to look up by the URL ID



# Razorpay order creation, before paying to razorpay for tournament registration, we have to create an order id and after payment successful
#    in that order id then go forward with registering participant into the tournament, need to look some edge cases here

razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))



# Now generate order id
class GenerateOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        tournament = get_object_or_404(Tournament, pk = pk)

        # before letting them pay, we should check some basic checks in tournament
        if tournament.status != 'REGISTRATION':
            return Response({'error': 'Registration closed'}, status= status.HTTP_400_BAD_REQUEST)
        
        if tournament.participants.count() >= tournament.max_players:
            return Response({'error': 'Tournament is full'}, status= status.HTTP_400_BAD_REQUEST)
        
        # stop duplicate payments before order is even created
        if Participant.objects.filter(tournament = tournament, user = request.user).exists():
            return Response({'error': 'You already registerd for this tournament'}, status= status.HTTP_400_BAD_REQUEST)
        

        # check whether tournament has entry fee
        if tournament.entry_fee == Decimal('0.00'):
            return Response({'error': 'This is a free tournament, no payment required.'}, status = status.HTTP_400_BAD_REQUEST)
        
        # now create the order, razorpay requires the lowest metric of a currency
        amount_in_paise = int(tournament.entry_fee * 100)

        unique_recipt = f"tourney_{tournament.id}_user_{request.user.id}_{uuid.uuid4().hex[:6]}"

        try:
            razorpay_order = razorpay_client.order.create({
                'amount': amount_in_paise,
                'currency': 'INR',
                'receipt' : unique_recipt,
                'payment_capture' : '1'  # Let the money to be captured by razorpay right after user enters pin, if 0 instead of 1
                                         #    then money will be held by bank until i captures it
            })

            # Also save the order to our database
            Order.objects.create(
                user = request.user,
                tournament = tournament,
                razorpay_order_id = razorpay_order['id'],
                amount = int(tournament.entry_fee * 100)
            )


            # now send ordera_id back to react
            return Response({
                'order_id' : razorpay_order['id'],
                'amount' : amount_in_paise,
                'currency': 'INR'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    




class RegisterTournamentView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        game_id = request.data.get('game_id')

        # first lock a row in tournament to check availability safely
        tournament = get_object_or_404(Tournament.objects.select_for_update(), pk = pk)

        # check for double entry
        if Participant.objects.filter(tournament = tournament, user = request.user).exists():
            return Response({'error': 'Already registered for this tournament'}, status= status.HTTP_400_BAD_REQUEST)
        

        # --> 1. If tournament is free
        if tournament.entry_fee == Decimal('0.00'):
            if tournament.participants.count() >= tournament.max_players:
                return Response({'error': 'Tournament is full'}, status= status.HTTP_400_BAD_REQUEST)
            
            try:
                # Register them instantly if slot is available
                Participant.objects.create(tournament = tournament, user= request.user, game_id = game_id)
                return Response({
                    'message': 'Successfully registered for tournament',
                    'new_prize_pool' : tournament.current_prize_pool
                }, status= status.HTTP_201_CREATED)
            except IntegrityError:
                return Response({'error': 'You already Registered'}, status=status.HTTP_400_BAD_REQUEST)
        
        # --> 2. If tournament is paid
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_order_id = request.data.get('razorpay_order_id')
        razorpay_signature = request.data.get('razorpay_signature')

        # check does the react do sends payment data
        if not all ([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
            return Response({'error': 'missing payment data'}, status= status.HTTP_400_BAD_REQUEST)
        
        try:
            razorpay_client.utility.verify_payment_signature({
                'razorpay_payment_id' : razorpay_payment_id,
                'razorpay_order_id' : razorpay_order_id,
                'razorpay_signature' : razorpay_signature
            })

        except razorpay.errors.SignatureVerificationError:
            return Response({'error': 'Invalid Payment Signature'}, status= status.HTTP_400_BAD_REQUEST)
        


        # Order validation from Database
        try:
            db_order = Order.objects.get(razorpay_order_id = razorpay_order_id)

            # make sure this order belongs to the same user and tournament
            if db_order.user != request.user or db_order.tournament != tournament:
                return Response({'error': 'Cross Payment tampering detected'}, status= status.HTTP_403_FORBIDDEN)
            
            # Preventing cheap order swaping
            if db_order.amount != tournament.entry_fee:
                return Response({'error': 'Payment amount mismatch detected'}, status= status.HTTP_400_BAD_REQUEST)
            
            # Check if they are using already paid order's id, prevent double use
            if db_order.is_paid:
                return Response({'error': 'This order has already been processed'}, status= status.HTTP_400_BAD_REQUEST)

            
        except Order.DoesNotExist:
            return Response({'error':'Order not found in our records'}, status= status.HTTP_404_NOT_FOUND)
        
        # Check the payment is captured ?
        try:
            payment_details = razorpay_client.payment.fetch(razorpay_payment_id)
            if payment_details['status'] != 'captured':
                return Response({'error':'Payment has not been captured by bank'}, status= status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({'error':'could not verify payment details with razorpay'}, status= status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Refund if slots gets filled up in between process
        if tournament.participants.count() >= tournament.max_players:
            refund_amount = int(tournament.entry_fee * 100)
            razorpay_client.payment.refund(razorpay_payment_id, {'amount': refund_amount})
            return Response({
                'error': 'Oops, Tournament filled up, You have been refunded! A new tournament will be open soon 🫡'
                }, status= status.HTTP_400_BAD_REQUEST)
                
        
        try:
            # if everything is okay, then register the paying user
            Participant.objects.create(tournament= tournament, user = request.user, game_id = game_id)
            db_order.is_paid = True
            db_order.save()

            return Response({
                'message':'Payment Successfull, joined tournament',
                'new_prize_pool' : tournament.current_prize_pool
            }, status= status.HTTP_201_CREATED)
        
        except IntegrityError:
            # if this block is hit, it means user paid but db rejected the duplicate entry
            refund_amount = int(tournament.entry_fee * 100)
            razorpay_client.payment.refund(razorpay_payment_id, {'amount': refund_amount})
            return Response({'error':'You are already registered. Your duplicate payment has been refunded'}, status= status.HTTP_400_BAD_REQUEST)
        





@api_view(['GET'])
@permission_classes([AllowAny])
def game_tournaments(request, game_id):
    tournaments = Tournament.objects.filter(game_id = game_id).order_by('-created_at')
    serializer = TournamentSerializer(tournaments, many = True, context = {'request': request})
    return Response(serializer.data)