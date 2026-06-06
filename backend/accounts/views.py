from django.shortcuts import render
from django.contrib.auth import get_user_model,authenticate
from rest_framework import generics
from rest_framework.decorators import api_view,authentication_classes,permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.text import slugify
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from .serializers import UserProfileSerializer, WalletTransactionSerializer

# Google
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests  # import like this to avooid conflicts

# Create your views here.

User = get_user_model()






class MyProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get the profile of the currently logged-in user
        profile = request.user.profile 
        serializer = UserProfileSerializer(profile, context={'request': request})
        return Response(serializer.data)

    def patch(self, request):
        # 1. Get the current user's profile
        profile = request.user.profile
        
        # 2. Pass the incoming data (which includes the image files) to the serializer
        # partial=True means we don't require EVERY field to be sent, just the ones being updated
        serializer = UserProfileSerializer(
            profile, 
            data=request.data, 
            partial=True, 
            context={'request': request}
        )
        
        # 3. Validate and save
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        # 4. If something goes wrong (e.g., wrong file type), return the error
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class TransactionHistoryView(generics.ListAPIView):
    serializer_class = WalletTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Return all transactions for the user, ordered newest to oldest
        return self.request.user.transactions.all().order_by('-created_at')





## Normal Register Veiw

@api_view(['POST'])
@authentication_classes([]) 
@permission_classes([AllowAny])
def register_user(request):
    email = request.data.get('email')
    username = request.data.get('username')
    password = request.data.get('password')

    if username is None or email is None or password is None:
        return Response({'message': 'Please provide all fields'}, status= status.HTTP_400_BAD_REQUEST)
    
    if User.objects.filter(username = username).exists():
        return Response({'message' : 'Username already taken'}, status= status.HTTP_400_BAD_REQUEST)
    
    if User.objects.filter(email = email).exists():
        return Response({'message' : 'Email you provided already linked to another account'}, status= status.HTTP_400_BAD_REQUEST)
    
    user = User.objects.create_user(username= username, email= email, password= password)
    refresh = RefreshToken.for_user(user)

    return Response({
        'username' : user.username,
        'id' : user.id,
        'access_token' : str(refresh.access_token),
        'refresh_token' : str(refresh)
    },
    status=status.HTTP_201_CREATED  )


# { 

#     "email" : "testemail",
#     "username": "testuser",
#     "password": "testpassword"
# }


## Normal Login view

@api_view(['POST'])
@authentication_classes([]) 
@permission_classes([AllowAny])
def login_user(request):
    email = request.data.get('email')
    password = request.data.get('password')

    user = authenticate(email = email, password = password)

    if user is not None:
        refresh = RefreshToken.for_user(user)
        return Response({
            'username' : user.username,
            'id' : user.id,
            'access_token' : str(refresh.access_token),
            'refresh_token' : str(refresh)
        },
        status = status.HTTP_200_OK)
    
    else:
        return Response({'message': 'check username and password'}, status= status.HTTP_401_UNAUTHORIZED)
    


# {
#     "email": "testemail",
#      "password": "testpassword"
# }



#       <--------------Google Login setup------------------->

#  first create a function to generate unique username

def generate_unique_username(base_name):
    base_name = slugify(base_name)
    username = base_name
    counter = 1
    while User.objects.filter(username = username).exists():
        username = f"{username}{counter}"    # adds number to last when username already exists
        counter += 1
    return username


# google login view
class GoogleLoginView(APIView):
    def post(self, request):
        token = request.data.get('token')

        if not token:
            return Response({'message': 'No token received'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            idinfo = id_token.verify_oauth2_token(
                token,google_requests.Request(),
                settings.GOOGLE_CLIENT_ID
            )

            email = idinfo.get('email')
            name = idinfo.get('name')
            sub = idinfo.get('sub') # sub is the unique identfier for user

            user, created = User.objects.get_or_create(
                email = email,
                defaults = {
                    'username' : generate_unique_username(name),  # to create a unique username
                    'first_name' : name
                }
            )

            refresh = RefreshToken.for_user(user)
            return Response({
                'username' : user.username,
                'id' : user.id,
                'access_token' : str(refresh.access_token),
                'refresh_token' : str(refresh)

            }, status= status.HTTP_200_OK)

        except ValueError:
            return Response({'message' : 'Invalid token'}, status= status.HTTP_400_BAD_REQUEST)  
        





