import requests
from django.shortcuts import render
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework import status, generics, permissions
from .models import Stream, Games
from .serializers import StreamOwnerSerializer, StreamUpdateSerializer, StreamPublicSerializer
from django.db.models import Q

from tournaments.models import Tournament



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
       

       
class CreateStreamView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # 1. Check if user already has a channel
        if hasattr(user, 'stream'):
            return Response(
                {"message": "You already have a stream channel"},
                status=status.HTTP_400_BAD_REQUEST
            )    
        
        # 2. Extract ALL data from the React form payload
        stream_type = request.data.get('stream_type', 'CLOUDFLARE')
        external_url = request.data.get('external_url', '')
        title = request.data.get('title', f"{user.username}'s Stream")
        description = request.data.get('description', '')
        
        # Handle booleans properly from JSON
        is_live_data = request.data.get('is_live', False)
        is_live = str(is_live_data).lower() == 'true' if isinstance(is_live_data, str) else bool(is_live_data)
        
        game_id = request.data.get('game_id')
        active_tournament_id = request.data.get('active_tournament_id')

        # 3. Get Game and Tournament instances if they were provided
        game_instance = Games.objects.filter(id=game_id).first() if game_id else None
        tournament_instance = Tournament.objects.filter(id=active_tournament_id).first() if active_tournament_id else None

        # ==========================================
        # PATH A: CLOUDFLARE
        # ==========================================
        if stream_type == 'CLOUDFLARE':
            cloudflare_url = f"https://api.cloudflare.com/client/v4/accounts/{settings.CLOUDFLARE_ACCOUNT_ID}/stream/live_inputs"
            headers = {
                "Authorization": f"Bearer {settings.CLOUDFLARE_API_TOKEN}",
                "Content-Type": "application/json"
            }
            data = {
                "meta": {"name": f"{user.username}'s Stream"},
                "recording": { "mode": "automatic", "timeout": 0 } 
            }

            try:
                response = requests.post(cloudflare_url, headers=headers, json=data)
                response_data = response.json()

                if response.status_code in [200, 201] and response_data.get('success'):
                    result = response_data['result']
                    
                    stream = Stream.objects.create(
                        user=user,
                        stream_type='CLOUDFLARE',
                        cloudflare_id=result.get('uid'),
                        stream_key=result['rtmps']['streamKey'],
                        playback_id=result.get('uid'),
                        title=title,
                        description=description,
                        is_live=is_live,
                        game=game_instance,
                        active_tournament=tournament_instance
                    )
                    serializer = StreamOwnerSerializer(stream)
                    return Response(serializer.data, status=status.HTTP_201_CREATED)
                else:
                    return Response({"message": "Failed to connect to Cloudflare"}, status=status.HTTP_502_BAD_GATEWAY)
            except requests.exceptions.RequestException:
                return Response({"message": "Error connecting to Provider."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # ==========================================
        # PATH B: YOUTUBE OR TWITCH (No API Call)
        # ==========================================
        elif stream_type in ['YOUTUBE', 'TWITCH']:
            if not external_url:
                return Response({"message": f"External URL is required for {stream_type}"}, status=status.HTTP_400_BAD_REQUEST)

            stream = Stream.objects.create(
                user=user,
                stream_type=stream_type,
                external_url=external_url,
                title=title,
                description=description,
                is_live=is_live,
                game=game_instance,
                active_tournament=tournament_instance
            )
            serializer = StreamOwnerSerializer(stream)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        else:
            return Response({"message": "Invalid Stream Type"}, status=status.HTTP_400_BAD_REQUEST)


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
        
        # avoid hitting cloudflare if using Youtube/Twitch
        if stream.stream_type != 'CLOUDFLARE':
            return Response({
                'message':'External Stream services (youtube/twitch) do not provide RTMP keys here'
            }, status= status.HTTP_400_BAD_REQUEST)
        

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
    permission_classes = [AllowAny]
    queryset = Stream.objects.filter(is_live = True)
    serializer_class = StreamPublicSerializer



# view for watching the selected stream
class StreamDetailVeiw(RetrieveAPIView):
    queryset = Stream.objects.filter(is_live = True)
    serializer_class = StreamPublicSerializer








# --- EXISTING VIEWS (Create, Get, etc.) WOULD BE HERE ---

# 1. Update Stream View
class UpdateStreamView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StreamUpdateSerializer

    def get_object(self):
        try:
            return Stream.objects.get(user = self.request.user)
        except Stream.DoesNotExist:
            raise NotFound(detail= 'No stream Found, Create Your Stream Channel First.')



@api_view(['GET'])
@permission_classes([AllowAny])
def game_streams(request, game_id):
    # Only fetch streams that are currently LIVE for this specific game
    streams = Stream.objects.filter(game_id=game_id, is_live=True).order_by('-created_at')
    serializer = StreamPublicSerializer(streams, many=True)
    return Response(serializer.data)