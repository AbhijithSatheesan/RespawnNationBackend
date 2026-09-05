from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
import razorpay
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import UserProfile, WalletTransaction
from .models import Order, Participant, Tournament

User = get_user_model()


class EssentialTournamentsTests(APITestCase):

    def setUp(self):
        cache.clear()

        # Pass unique emails to satisfy the unique email constraint on your custom user model
        self.user1 = User.objects.create_user(
            username="player1", email="player1@example.com", password="password123"
        )
        self.user2 = User.objects.create_user(
            username="player2", email="player2@example.com", password="password123"
        )

        # Use get_or_create to prevent integrity errors if post_save signals auto-create profiles
        self.profile1, _ = UserProfile.objects.get_or_create(user=self.user1)
        self.profile1.wallet_balance = Decimal("500.00")
        self.profile1.save()

        self.profile2, _ = UserProfile.objects.get_or_create(user=self.user2)
        self.profile2.wallet_balance = Decimal("10.00")
        self.profile2.save()

        self.tournament = Tournament.objects.create(
            title="Tekken 8 Championship",
            status="REGISTRATION",
            entry_fee=Decimal("100.00"),
            max_players=2,
            registration_deadline="2026-12-01T00:00:00Z",
        )

    # -------------------------------------------------------------------------
    # 1. REDIS CACHING
    # -------------------------------------------------------------------------
    def test_tournament_list_redis_cache_hit_and_miss(self):
        """Verify first request populates cache and second request reads from Redis."""
        url = reverse("tournament-list")
        cache_key = "tournaments_list_status_all_page_1_ps_10"

        # 1. Cache starts empty
        self.assertIsNone(cache.get(cache_key))

        # 2. First request -> Cache Miss (fetches DB & writes to Redis)
        res1 = self.client.get(url)
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        # 3. Cache should now hold payload
        cached_data = cache.get(cache_key)
        self.assertIsNotNone(cached_data)

        # 4. Second request -> Served from Redis
        res2 = self.client.get(url)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data, cached_data)

    # -------------------------------------------------------------------------
    # 2. WALLET PAYMENTS
    # -------------------------------------------------------------------------
    def test_register_wallet_success(self):
        """Verify successful wallet checkout deducts balance, logs transaction, and joins."""
        self.client.force_authenticate(user=self.user1)
        url = reverse("register-tournament", kwargs={"pk": self.tournament.pk})

        data = {"payment_method": "WALLET", "game_id": "Gamer_001"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.profile1.refresh_from_db()
        self.assertEqual(self.profile1.wallet_balance, Decimal("400.00"))

        self.assertTrue(
            Participant.objects.filter(
                tournament=self.tournament, user=self.user1
            ).exists()
        )
        self.assertTrue(
            WalletTransaction.objects.filter(
                user=self.user1, transaction_type="ENTRY_FEE"
            ).exists()
        )

    def test_register_wallet_insufficient_balance(self):
        """Verify user with lower balance than entry fee is blocked."""
        self.client.force_authenticate(user=self.user2)
        url = reverse("register-tournament", kwargs={"pk": self.tournament.pk})

        data = {"payment_method": "WALLET", "game_id": "Gamer_002"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Insufficient wallet balance", response.data["error"])

        self.profile2.refresh_from_db()
        self.assertEqual(self.profile2.wallet_balance, Decimal("10.00"))

    # -------------------------------------------------------------------------
    # 3. PAYMENT SECURITY & TAMPERING
    # -------------------------------------------------------------------------
    @patch("tournaments.views.razorpay_client")
    def test_register_razorpay_invalid_signature_rejected(self, mock_razorpay):
        """Verify invalid Razorpay signature is rejected."""
        mock_razorpay.utility.verify_payment_signature.side_effect = (
            razorpay.errors.SignatureVerificationError()
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse("register-tournament", kwargs={"pk": self.tournament.pk})

        data = {
            "payment_method": "RAZORPAY",
            "razorpay_payment_id": "pay_fake123",
            "razorpay_order_id": "order_fake123",
            "razorpay_signature": "bad_signature",
            "game_id": "Gamer_001",
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid Payment Signature", response.data["error"])

    @patch("tournaments.views.razorpay_client")
    def test_register_razorpay_cross_user_order_tampering(self, mock_razorpay):
        """Verify user cannot use another user's paid Order ID."""
        mock_razorpay.utility.verify_payment_signature.return_value = True

        Order.objects.create(
            user=self.user2,
            tournament=self.tournament,
            razorpay_order_id="order_user2_100",
            amount=10000,
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse("register-tournament", kwargs={"pk": self.tournament.pk})

        data = {
            "payment_method": "RAZORPAY",
            "razorpay_payment_id": "pay_stolen_123",
            "razorpay_order_id": "order_user2_100",
            "razorpay_signature": "valid_sig",
            "game_id": "Gamer_001",
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Cross Payment tampering detected", response.data["error"])

    # -------------------------------------------------------------------------
    # 4. BUSINESS LOGIC & EDGE CASES
    # -------------------------------------------------------------------------
    def test_register_duplicate_entry_prevented(self):
        """Verify already registered user cannot join again."""
        Participant.objects.create(
            tournament=self.tournament, user=self.user1, game_id="Gamer_001"
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse("register-tournament", kwargs={"pk": self.tournament.pk})

        data = {"payment_method": "WALLET", "game_id": "Gamer_001"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Already registered", response.data["error"])

    @patch("tournaments.views.razorpay_client")
    def test_register_razorpay_full_tournament_triggers_refund(self, mock_razorpay):
        """Verify refund is triggered if slots fill up before payment confirmation."""
        mock_razorpay.utility.verify_payment_signature.return_value = True
        mock_razorpay.payment.fetch.return_value = {"status": "captured"}

        u3 = User.objects.create_user(username="u3", email="u3@example.com")
        u4 = User.objects.create_user(username="u4", email="u4@example.com")
        Participant.objects.create(tournament=self.tournament, user=u3, game_id="p3")
        Participant.objects.create(tournament=self.tournament, user=u4, game_id="p4")

        Order.objects.create(
            user=self.user1,
            tournament=self.tournament,
            razorpay_order_id="order_late_123",
            amount=10000,
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse("register-tournament", kwargs={"pk": self.tournament.pk})

        data = {
            "payment_method": "RAZORPAY",
            "razorpay_payment_id": "pay_late_123",
            "razorpay_order_id": "order_late_123",
            "razorpay_signature": "valid_sig",
            "game_id": "LatePlayer",
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("refunded", response.data["error"])

        mock_razorpay.payment.refund.assert_called_once_with(
            "pay_late_123", {"amount": 10000}
        )