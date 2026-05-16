from django.db import models
from django.conf import settings
from tournaments.models import Tournament
from games.models import Games

# Create your models here.



class ChatRoom(models.Model):
    ROOM_TYPES = [
        ('GLOBAL' , 'Global Community'),
        ('GAME' , 'Game Discussions'),
        ('TOURNAMENT', 'Tournament Lobby'),
    ]

    name = models.CharField(max_length= 100, help_text='e.g. Sekiro General, X tournament ....')
    room_type = models.CharField(max_length= 20, choices= ROOM_TYPES)

    # Links
    tournament = models.ForeignKey(Tournament, on_delete= models.CASCADE, null= True, blank= True, related_name='chat_rooms')
    game = models.ForeignKey(Games, on_delete= models.CASCADE, null= True, blank= True, related_name='chat_rooms')

    # Incase we want a private chatroom
    is_private = models.BooleanField(default= False)
    created_at = models.DateTimeField(auto_now_add= True)


    def __str__(self):
        return f"[{self.get_room_type_display()}] {self.name}"
    

# To save the messages

class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete= models.CASCADE, related_name= 'messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete= models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add= True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username} : {self.text[:20]}..."



