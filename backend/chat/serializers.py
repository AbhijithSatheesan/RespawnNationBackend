from rest_framework import serializers
from .models import ChatMessage




class ChatMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source= 'sender.username', read_only = True)

    class Meta:
        model = ChatMessage
        fields = ['id', 'room', 'sender','sender_username', 'text', 'created_at']