import requests
from django.shortcuts import render
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Stream
from .serializers import (
    StreamPublicSerializer,
    StreamOwnerSerializer,
)


# Create your views here.


# view for going live 
class MyStreamView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            stream = request.user.stream
            serializer = StreamOwnerSerializer(stream)
            return Response(serializer.data)
        except Stream.DoesNotExist:
            return Response(
                {"message": "No Stream found. Please create one"},
                status= status.HTTP_404_NOT_FOUND
            )
       

       

# Vieww to create a stream
class CreateStreamVIew(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # first check if user already have an account
        if hasattr(user, 'stream'):
            return Response(
                {"message": "You already have a stream channel"},
                status= status.HTTP_400_BAD_REQUEST
            )    
        
        cloudflare_url = f"https://api.cloudflare.com/client/v4/accounts/{settings.CLOUDFLARE_ACCOUNT_ID}/stream/live_inputs"
        headers = {
            "Authorization" : f"Bearer {settings.CLOUDFLARE_API_TOKEN}",
            "Content-Type" : "application/json"
        }
        data = {
            "meta": {"name": f"{user.username}'s Stream"},
            "recording": { "mode": "automatic",
                           "timeout": 0 } 
        }

        try:
            response = requests.post(cloudflare_url, headers= headers, json= data)
            response_data = response.json()

            print(f"Cloudflare Status: {response.status_code}")
            print(f"Cloudflare Response: {response_data}")

            if response.status_code in [200, 201] and response_data.get('success'):
                result = response_data['result']

                # If all above worked fine, then add the data to stream model

                stream = Stream.objects.create(
                    user = user,
                    cloudflare_id = result.get('uid'),
                    stream_key = result['rtmps']['streamKey'],
                    playback_id = result.get('uid'),
                    title = f"{user.username}'s first Stream"
                )

                serializer = StreamOwnerSerializer(stream)
                return Response(serializer.data, status= status.HTTP_201_CREATED)
            
            else:
                return Response(
                    {"message":"Failed to create Stream", "errors":response_data.get('errors')},
                    status= status.HTTP_502_BAD_GATEWAY
                )
            
        except requests.exceptions.RequestException as e:
            return Response(
                {"message": "Error connecting to Stream Provider."},
                status= status.HTTP_503_SERVICE_UNAVAILABLE
            )




# streams/views.py
import requests # Ensure this is imported
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Stream
from .serializers import StreamOwnerSerializer

class RegenerateStreamKeyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        
        # 1. Get the existing stream object
        try:
            stream = user.stream
        except Stream.DoesNotExist:
            return Response(
                {"message": "No stream found to regenerate. Please create one first."}, 
                status=status.HTTP_404_NOT_FOUND
            )

        headers = {
            "Authorization": f"Bearer {settings.CLOUDFLARE_API_TOKEN}",
            "Content-Type": "application/json"
        }

        # 2. DELETE existing input on Cloudflare (Clean up old garbage)
        if stream.cloudflare_id:
            delete_url = f"https://api.cloudflare.com/client/v4/accounts/{settings.CLOUDFLARE_ACCOUNT_ID}/stream/live_inputs/{stream.cloudflare_id}"
            try:
                # We try to delete, but pass if it fails (maybe it was already deleted manually)
                requests.delete(delete_url, headers=headers)
            except requests.exceptions.RequestException:
                pass 

        # 3. CREATE new input on Cloudflare
        create_url = f"https://api.cloudflare.com/client/v4/accounts/{settings.CLOUDFLARE_ACCOUNT_ID}/stream/live_inputs"
        data = {
            "meta": {"name": f"{user.username}'s Stream (Reset)"},
            "recording": { "mode": "off" } 
        }

        try:
            response = requests.post(create_url, headers=headers, json=data)
            response_data = response.json()

            # Check for 200 or 201 success
            if response.status_code in [200, 201] and response_data.get('success'):
                result = response_data['result']

                # 4. UPDATE your specific model fields
                stream.cloudflare_id = result.get('uid')
                stream.stream_key = result['rtmps']['streamKey']
                stream.playback_id = result.get('uid')
                
                # Force stream offline since we just killed the input
                stream.is_live = False 
                
                stream.save()

                serializer = StreamOwnerSerializer(stream)
                return Response(serializer.data, status=status.HTTP_200_OK)
            
            else:
                return Response(
                    {"message": "Failed to generate new key", "errors": response_data.get('errors')}, 
                    status=status.HTTP_502_BAD_GATEWAY
                )

        except requests.exceptions.RequestException:
            return Response(
                {"message": "Error connecting to provider."}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )




# veiw for seeing list of streams
class LiveStreamsListView(ListAPIView):
    queryset = Stream.objects.filter(is_live = True)
    serializer_class = StreamPublicSerializer



# view for watching the selected stream
class StreamDetailVeiw(RetrieveAPIView):
    queryset = Stream.objects.filter(is_live = True)
    serializer_class = StreamPublicSerializer







from rest_framework import generics, status, permissions
from rest_framework.response import Response
from django.db.models import Q
from .models import Stream, Games
from .serializers import StreamUpdateSerializer 

# --- EXISTING VIEWS (Create, Get, etc.) WOULD BE HERE ---

# 1. Update Stream View
class UpdateStreamView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StreamUpdateSerializer

    def get_object(self):
        # Ensure user can only update their OWN stream
        return Stream.objects.get(user=self.request.user)

