from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import ChatRoom, ChatMessage
from tournaments.models import Participant, Tournament
from games.models import Games

from .serializers import ChatMessageSerializer



# Send chat message

class SendMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, room_id):
        room = get_object_or_404(ChatRoom, id = room_id)
        text = request.data.get('text')

        if not text or not text.strip():
            return Response({'error': 'Message cannot be empty'}, status= status.HTTP_400_BAD_REQUEST)
        
        # security chck for tournament
        if room.room_type == 'TOURNAMENT':
            is_registered = Participant.objects.filter(tournament = room.tournament, user = request.user).exists()
            if not is_registered:
                return Response({'error': 'You are not allowed to message here'}, status= status.HTTP_403_FORBIDDEN)
        

        # If the room type is global or games, anyone logged in can send messages

        message = ChatMessage.objects.create(
            room = room,
            sender = request.user,
            text = text.strip()
        )

        return Response({
            'message': 'message sent successfully',
            'msg_id' : message.id
        }, status= status.HTTP_201_CREATED)
    



class GetRoomView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self,request):
        room_type = request.query_params.get('type', 'GLOBAL').upper()
       

        # For Global community
        if room_type == 'GLOBAL':
            room, created = ChatRoom.objects.get_or_create(
                room_type = 'GLOBAL',
                defaults = {'name' : 'The Nexus'}
            )
            return Response({
                'room_id' : room.id, 'room_name' : room.name
            })
        
        # Game specific chats
        elif room_type == 'GAME':
            game_id = request.query_params.get('game_id')
            if not game_id:
                return Response({'error':'Game id is required'}, status= status.HTTP_400_BAD_REQUEST)
            game = get_object_or_404(Games, pk = game_id)
            room, created = ChatRoom.objects.get_or_create(
                room_type = 'GAME',
                game = game,
                defaults= {'name' : f'{game.name} Hub'}
            )
            return Response({
                'room_id': room.id, 'room_name' : room.name
            })
        
        # If its a torunament chat
        elif room_type == 'TOURNAMENT':
            tournament_id = request.query_params.get('tournament_id')
            if not tournament_id:
                return Response({'error': 'Tournament id is required'}, status= status.HTTP_400_BAD_REQUEST)
            tournament = get_object_or_404(Tournament, pk = tournament_id)
            room, created = ChatRoom.objects.get_or_create(
                room_type = 'TOURNAMENT',
                tournament = tournament,
                defaults = {'name' : f'{tournament.title} Hub'}
            )
            return Response({
                'room_id' : room.id, 'room_name' : room.name
            })
            
            
            


class MessageHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, room_id):
        messages = ChatMessage.objects.filter(room_id = room_id).order_by('-created_at')[:50]

        # Return the oldest first for the chat UI
        serializer = ChatMessageSerializer(reversed(messages), many = True)

        return Response(serializer.data)




