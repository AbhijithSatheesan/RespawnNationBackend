from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import ChatRoom, ChatMessage
from tournaments.models import Participant, Tournament
from games.models import Games
from rest_framework.pagination import PageNumberPagination
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
            is_registered = Participant.objects.filter(tournament = room.tournament, user = request.user).exists() or request.user.is_staff
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
        # 1. Grab pagination query limits from React (Default to page 1, 25 items per page)
        page = int(request.query_params.get('page', 1))
        page_size = 25
        
        offset = (page - 1) * page_size
        limit = offset + page_size

        # 2. Add 'is_deleted=False' to your query filter
        all_messages = ChatMessage.objects.filter(
            room_id=room_id, 
            is_deleted=False
        ).order_by('-created_at')

        # Check if there are more messages beyond this current slice
        total_count = all_messages.count()
        has_next = total_count > limit

        # Slice the database query dynamically based on the current page page
        sliced_messages = all_messages[offset:limit]

        # Return oldest first for the frontend chat sequence layout
        serializer = ChatMessageSerializer(reversed(sliced_messages), many=True)

        # 3. Return both the messages AND the pagination metadata
        return Response({
            "results": serializer.data,
            "has_more": has_next
        })




# <<---------------------------Delete message (we will do a soft delete)----------------------->>
class DeleteChatMessage(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, message_id):
        message = get_object_or_404(ChatMessage, id = message_id)
        user = request.user

        # check who is do it
        if user == message.sender or user.is_staff:
            message.is_deleted = True 
            message.save()

            # Return a 204 after deletion, its a restful stantard
            return Response(status= status.HTTP_204_NO_CONTENT)
    
        else:
            return Response(
                {'error': 'You are not authorized to do this'},
                status= status.HTTP_403_FORBIDDEN
            )
