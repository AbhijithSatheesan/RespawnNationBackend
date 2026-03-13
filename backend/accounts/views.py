from django.shortcuts import render
from django.contrib.auth import get_user_model,authenticate
from rest_framework.decorators import api_view,authentication_classes,permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

# Create your views here.

User = get_user_model()


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
            'accesstoken' : str(refresh.access_token),
            'refresh_token' : str(refresh)
        },
        status = status.HTTP_200_OK)
    
    else:
        return Response({'message': 'check username and password'}, status= status.HTTP_401_UNAUTHORIZED)
    


# {
#     "email": "testemail",
#      "password": "testpassword"
# }
