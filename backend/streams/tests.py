from unittest.mock import MagicMock, patch
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from games.models import Games
from streams.models import Stream

User = get_user_model()


class StreamViewsTests(APITestCase):

    def setUp(self):
        # Create users with unique email addresses
        self.user = User.objects.create_user(
            username="streamer", email="streamer@example.com", password="password123"
        )
        self.other_user = User.objects.create_user(
            username="viewer", email="viewer@example.com", password="password123"
        )
        self.game = Games.objects.create(name="Tekken 8")

    # 1. TEST CLOUDFLARE STREAM CREATION (MOCKED HTTP RESPONSE)
    @patch("requests.post")
    def test_create_cloudflare_stream_success(self, mock_post):
        # Simulate a successful JSON response from Cloudflare API
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "result": {
                "uid": "cf_mock_uid_123",
                "rtmps": {"streamKey": "cf_mock_stream_key_abc"},
            },
        }
        mock_post.return_value = mock_response

        self.client.force_authenticate(user=self.user)
        payload = {
            "stream_type": "CLOUDFLARE",
            "title": "Ranked Matches",
            "game_id": self.game.id,
        }

        response = self.client.post("/api/streams/create-stream/", payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Stream.objects.filter(user=self.user).exists())

        stream = Stream.objects.get(user=self.user)
        self.assertEqual(stream.cloudflare_id, "cf_mock_uid_123")
        self.assertEqual(stream.stream_key, "cf_mock_stream_key_abc")

    # 2. TEST YOUTUBE STREAM CREATION (NO API CALL REQUIRED)
    def test_create_youtube_stream_success(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "stream_type": "YOUTUBE",
            "external_url": "https://youtube.com/live/example_id",
            "title": "YouTube Tournament Broadcast",
        }

        response = self.client.post("/api/streams/create-stream/", payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        stream = Stream.objects.get(user=self.user)
        self.assertEqual(stream.external_url, "https://youtube.com/live/example_id")

    # 3. TEST KEY REGENERATION (MOCKED CLOUDFLARE DELETE & POST)
    @patch("requests.delete")
    @patch("requests.post")
    def test_regenerate_stream_key_success(self, mock_post, mock_delete):
        # Existing Cloudflare stream in DB
        stream = Stream.objects.create(
            user=self.user,
            stream_type="CLOUDFLARE",
            cloudflare_id="old_uid_111",
            stream_key="old_key_111",
            is_live=True,
        )

        # Mock Cloudflare create response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "result": {
                "uid": "new_uid_222",
                "rtmps": {"streamKey": "new_key_222"},
            },
        }
        mock_post.return_value = mock_response

        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("regenerate-key"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify database update
        stream.refresh_from_db()
        self.assertEqual(stream.cloudflare_id, "new_uid_222")
        self.assertEqual(stream.stream_key, "new_key_222")
        self.assertFalse(stream.is_live)  # Key reset forces stream offline

    # 4. TEST PUBLIC LIVE LISTING (MUST ONLY RETURN LIVE STREAMS)
    def test_live_streams_list_filters_offline(self):
        # Create one live stream and one offline stream
        Stream.objects.create(
            user=self.user,
            stream_type="YOUTUBE",
            external_url="https://youtube.com/live/1",
            is_live=True,
        )
        Stream.objects.create(
            user=self.other_user,
            stream_type="YOUTUBE",
            external_url="https://youtube.com/live/2",
            is_live=False,
        )

        response = self.client.get("/api/streams/live/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Handles both paginated dict response and standard list response
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        self.assertEqual(len(results), 1)