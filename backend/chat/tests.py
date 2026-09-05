from datetime import timedelta
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from games.models import Games
from tournaments.models import Participant, Tournament
from .models import ChatMessage, ChatRoom

User = get_user_model()


class EssentialChatTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="gamer1", email="gamer1@example.com", password="password123"
        )
        self.other_user = User.objects.create_user(
            username="gamer2", email="gamer2@example.com", password="password123"
        )
        self.staff_user = User.objects.create_user(
            username="admin", email="admin@example.com", password="password123", is_staff=True
        )

        self.game = Games.objects.create(name="Tekken 8")
        self.tournament = Tournament.objects.create(
            title="Tekken Showdown",
            game=self.game,
            registration_deadline=timezone.now() + timedelta(days=2)
        )

        self.global_room = ChatRoom.objects.create(room_type="GLOBAL", name="The Nexus")
        self.tournament_room = ChatRoom.objects.create(
            room_type="TOURNAMENT", tournament=self.tournament, name="Tournament Hub"
        )

    def test_basic_chat_flow(self):
        self.client.force_authenticate(user=self.user)

        # 1. Send message
        send_url = reverse("send-message", kwargs={"room_id": self.global_room.id})
        send_res = self.client.post(send_url, {"text": "GG WP"})
        self.assertEqual(send_res.status_code, status.HTTP_201_CREATED)

        # 2. Fetch history
        history_url = reverse("chat-history", kwargs={"room_id": self.global_room.id})
        history_res = self.client.get(history_url)
        self.assertEqual(history_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(history_res.data["results"]), 1)

    def test_tournament_room_access_control(self):
        url = reverse("send-message", kwargs={"room_id": self.tournament_room.id})

        # Non-registered user blocked
        self.client.force_authenticate(user=self.user)
        res_blocked = self.client.post(url, {"text": "Can I chat?"})
        self.assertEqual(res_blocked.status_code, status.HTTP_403_FORBIDDEN)

        # Registered participant allowed
        Participant.objects.create(tournament=self.tournament, user=self.user)
        res_allowed = self.client.post(url, {"text": "Ready to play!"})
        self.assertEqual(res_allowed.status_code, status.HTTP_201_CREATED)

    def test_soft_deleted_messages_filtered_from_history(self):
        ChatMessage.objects.create(room=self.global_room, sender=self.user, text="Active Msg")
        ChatMessage.objects.create(room=self.global_room, sender=self.user, text="Deleted Msg", is_deleted=True)

        self.client.force_authenticate(user=self.user)
        url = reverse("chat-history", kwargs={"room_id": self.global_room.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["text"], "Active Msg")

    def test_delete_message_permissions(self):
        message = ChatMessage.objects.create(room=self.global_room, sender=self.user, text="Bad msg")
        url = reverse("delete-message", kwargs={"message_id": message.id})

        # Unauthorized user blocked
        self.client.force_authenticate(user=self.other_user)
        res_forbidden = self.client.delete(url)
        self.assertEqual(res_forbidden.status_code, status.HTTP_403_FORBIDDEN)

        # Message sender allowed
        self.client.force_authenticate(user=self.user)
        res_success = self.client.delete(url)
        self.assertEqual(res_success.status_code, status.HTTP_204_NO_CONTENT)
        message.refresh_from_db()
        self.assertTrue(message.is_deleted)