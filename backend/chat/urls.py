from django.urls import path
from .views import GetRoomView, SendMessageView, MessageHistoryView

urlpatterns = [
    # Gets room info by type (GLOBAL) or by Tournament ID
    path('room/', GetRoomView.as_view(), name='get-room'),
    # Fetches previous messages
    path('room/<int:room_id>/history/', MessageHistoryView.as_view(), name='chat-history'),
    # Sends a new message
    path('room/<int:room_id>/send/', SendMessageView.as_view(), name='send-message'),
]