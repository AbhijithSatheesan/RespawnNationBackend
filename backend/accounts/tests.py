from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
import razorpay
from rest_framework import status
from rest_framework.test import APITestCase

from .models import UserProfile, WalletDepositOrder, WalletTransaction, WithdrawalRequest

User = get_user_model()


class AccountsAndWalletTests(APITestCase):

    def setUp(self):
        cache.clear()

        # Create base test user with explicit unique email
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="testpassword123",
        )

        # Ensure user profile exists and has initial wallet balance
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.profile.wallet_balance = Decimal("500.00")
        self.profile.save()

    # -------------------------------------------------------------------------
    # 1. USER AUTHENTICATION & PROFILE
    # -------------------------------------------------------------------------
    def test_register_user_success(self):
        url = reverse("register")
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "Password@123",
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access_token", response.data)
        self.assertEqual(response.data["username"], "newuser")

    def test_register_user_duplicate_email(self):
        url = reverse("register")
        data = {
            "username": "anotheruser",
            "email": "testuser@example.com",
            "password": "Password@123",
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already linked to another account", response.data["message"])

    def test_login_user_success(self):
        url = reverse("login")
        data = {"email": "testuser@example.com", "password": "testpassword123"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_login_user_invalid_credentials(self):
        url = reverse("login")
        data = {"email": "testuser@example.com", "password": "wrongpassword"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("accounts.views.id_token.verify_oauth2_token")
    def test_google_login_success(self, mock_verify):
        mock_verify.return_value = {
            "email": "googleuser@example.com",
            "name": "Google User",
            "sub": "1234567890",
        }

        url = reverse("googlelogin")
        response = self.client.post(url, {"token": "fake_google_token"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)
        self.assertTrue(
            User.objects.filter(email="googleuser@example.com").exists()
        )

    def test_my_profile_get_authenticated(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("myprofile")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # -------------------------------------------------------------------------
    # 2. WALLET WITHDRAWAL
    # -------------------------------------------------------------------------
    def test_request_withdrawal_success(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("wallet-withdraw")

        data = {"amount": "200.00", "upi_id": "test@upi"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.wallet_balance, Decimal("300.00"))
        self.assertTrue(
            WithdrawalRequest.objects.filter(
                user=self.user, upi_id="test@upi"
            ).exists()
        )

    def test_request_withdrawal_insufficient_balance(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("wallet-withdraw")

        data = {"amount": "1000.00", "upi_id": "test@upi"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Insufficient wallet balance", response.data["error"])

    # -------------------------------------------------------------------------
    # 3. WALLET DEPOSIT & RAZORPAY VERIFICATION
    # -------------------------------------------------------------------------
    @patch("accounts.wallet.razorpay_client")
    def test_generate_deposit_order_success(self, mock_razorpay):
        mock_razorpay.order.create.return_value = {
            "id": "order_dep_123",
            "amount": 50000,
            "currency": "INR",
        }

        self.client.force_authenticate(user=self.user)
        url = reverse("generate-deposit-order")

        response = self.client.post(url, {"amount": "500.00"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["order_id"], "order_dep_123")
        self.assertTrue(
            WalletDepositOrder.objects.filter(
                razorpay_order_id="order_dep_123"
            ).exists()
        )

    @patch("accounts.wallet.razorpay_client")
    def test_verify_deposit_success(self, mock_razorpay):
        mock_razorpay.utility.verify_payment_signature.return_value = True
        mock_razorpay.payment.fetch.return_value = {"status": "captured"}

        deposit_order = WalletDepositOrder.objects.create(
            user=self.user, razorpay_order_id="order_valid_123", amount=Decimal("200.00")
        )

        self.client.force_authenticate(user=self.user)
        url = reverse("verify-deposit")

        data = {
            "razorpay_payment_id": "pay_valid_123",
            "razorpay_order_id": "order_valid_123",
            "razorpay_signature": "valid_sig",
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.profile.refresh_from_db()
        deposit_order.refresh_from_db()

        self.assertEqual(self.profile.wallet_balance, Decimal("700.00"))
        self.assertTrue(deposit_order.is_paid)

    @patch("accounts.wallet.razorpay_client")
    def test_verify_deposit_invalid_signature(self, mock_razorpay):
        mock_razorpay.utility.verify_payment_signature.side_effect = (
            razorpay.errors.SignatureVerificationError()
        )

        self.client.force_authenticate(user=self.user)
        url = reverse("verify-deposit")

        data = {
            "razorpay_payment_id": "pay_fake_123",
            "razorpay_order_id": "order_fake_123",
            "razorpay_signature": "bad_sig",
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid Payment Signature", response.data["error"])

    # -------------------------------------------------------------------------
    # 4. UTILITIES & TRANSACTIONS
    # -------------------------------------------------------------------------
    def test_health_check(self):
        url = reverse("health-check")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"status": "awake"})

    def test_transaction_history_authenticated(self):
        WalletTransaction.objects.create(
            user=self.user,
            amount=Decimal("100.00"),
            transaction_type="DEPOSIT",
            description="Test Deposit",
        )

        self.client.force_authenticate(user=self.user)
        url = reverse("transaction-history")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)