import razorpay
from django.conf import settings
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from .models import Tournament,Participant
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
        
        # now create the order, razorpay requires the lowest metric of a currency
        amount_in_paise = 50000

        try:
            razorpay_order = razorpay_client.order.create({
                'amount': amount_in_paise,
                'currency': 'INR',
                'receipt' : f"tourney_{tournament.id}_user_{request.user.id}",
                'payment_capture' : '1'  # Let the money to be captured by razorpay right after user enters pin, if 0 instead of 1
                                         #    then money will be held by bank until i captures it
            })

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

    @transaction.atomic  # Either everything inside this will complete or nothing will complete
    def post(self, request, pk):
        # grab the data react sent to us after a successfull payment
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_order_id = request.data.get('razorpay_order_id')
        razorpay_signature = request.data.get('razorpay_signature')
        game_id = request.data.get('game_id') # user's game id

        try:
            razorpay_client.utility.verify_payment_signature({
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_order_id' : razorpay_order_id,
                'razorpay_signature' : razorpay_signature
            })
        except razorpay.errors.SignatureVerificationError:
            return Response({'error': 'Invalid payment Signature.'}, status= status.HTTP_400_BAD_REQUEST)
        
        # Lock the tournament row to check availability safely
        tournament = get_object_or_404(Tournament.objects.select_for_update(), pk = pk)

        # if the slots got filled while paying, refund the money automatically
        if tournament.participants.count() >= tournament.max_players:
            razorpay_client.payment.refund(razorpay_payment_id,{'amount': 50000})
            return Response({'error': 'Oops tournament filled up, you have been refunded. A new tournament will be open soon 🫡'}, status= status.HTTP_400_BAD_REQUEST)
        
        # if slots are available, then jsut add the participant to tournament
        participant = Participant.objects.create(
            tournament = tournament,
            user = request.user,
            game_id = game_id
        )

        return Response({'message': 'Successfully joined tournament'}, status= status.HTTP_201_CREATED)

        

