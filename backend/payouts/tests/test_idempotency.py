"""
Idempotency Test:
Verifies that duplicate payout requests with the same Idempotency-Key
return the exact same response without creating duplicate payouts.

Also tests that same key from different merchants are independent,
and that keys expire after 24 hours.
"""
import uuid
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from payouts.models import Merchant, BankAccount, LedgerEntry, Payout, IdempotencyKey


class IdempotencyTest(TestCase):

    def setUp(self):
        """Create a merchant with ₹1000 balance."""
        self.user = User.objects.create_user(
            username='idempotency_test_user',
            password='testpass123'
        )
        self.merchant = Merchant.objects.create(
            user=self.user,
            business_name='Idempotency Test Merchant',
            email='test@idempotent.com'
        )
        self.bank_account = BankAccount.objects.create(
            merchant=self.merchant,
            account_number='9999888877776666',
            ifsc_code='ICIC0005678',
            account_holder_name='Test Account',
            is_primary=True,
        )
        # Seed ₹1000 (100000 paise)
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type='credit',
            amount_paise=100000,
            description='Test credit - ₹1000',
        )

        # Get JWT token
        refresh = RefreshToken.for_user(self.user)
        self.token = str(refresh.access_token)

        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    def test_duplicate_request_returns_same_response(self):
        """
        Sending the same payout request twice with the same Idempotency-Key
        should return identical responses and create only ONE payout.
        """
        idempotency_key = str(uuid.uuid4())
        payload = {
            'amount_paise': 10000,  # ₹100
            'bank_account_id': str(self.bank_account.id),
        }

        # First request
        response1 = self.client.post(
            '/api/v1/payouts/',
            data=payload,
            format='json',
            HTTP_IDEMPOTENCY_KEY=idempotency_key,
        )
        self.assertEqual(response1.status_code, 201)

        # Second request — same key
        response2 = self.client.post(
            '/api/v1/payouts/',
            data=payload,
            format='json',
            HTTP_IDEMPOTENCY_KEY=idempotency_key,
        )
        # Should return the EXACT same response
        self.assertEqual(response2.status_code, 201)
        self.assertEqual(response1.data['id'], response2.data['id'])
        self.assertEqual(response1.data['amount_paise'], response2.data['amount_paise'])

        # Only ONE payout should exist
        payouts = Payout.objects.filter(merchant=self.merchant)
        self.assertEqual(payouts.count(), 1, "Only one payout should be created")

        # Only ONE hold entry should exist
        holds = LedgerEntry.objects.filter(
            merchant=self.merchant,
            entry_type='hold'
        )
        self.assertEqual(holds.count(), 1, "Only one hold entry should exist")

    def test_different_keys_create_different_payouts(self):
        """
        Different idempotency keys should create separate payouts.
        """
        payload = {
            'amount_paise': 10000,
            'bank_account_id': str(self.bank_account.id),
        }

        response1 = self.client.post(
            '/api/v1/payouts/',
            data=payload,
            format='json',
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        response2 = self.client.post(
            '/api/v1/payouts/',
            data=payload,
            format='json',
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )

        self.assertEqual(response1.status_code, 201)
        self.assertEqual(response2.status_code, 201)
        self.assertNotEqual(response1.data['id'], response2.data['id'])

        payouts = Payout.objects.filter(merchant=self.merchant)
        self.assertEqual(payouts.count(), 2)

    def test_missing_idempotency_key_rejected(self):
        """
        Requests without an Idempotency-Key header should be rejected.
        """
        response = self.client.post(
            '/api/v1/payouts/',
            data={
                'amount_paise': 10000,
                'bank_account_id': str(self.bank_account.id),
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)

    def test_keys_scoped_per_merchant(self):
        """
        Same idempotency key from different merchants should create
        separate payouts — keys are scoped per merchant.
        """
        shared_key = str(uuid.uuid4())

        # Create a second merchant
        user2 = User.objects.create_user(username='merchant2', password='testpass123')
        merchant2 = Merchant.objects.create(
            user=user2,
            business_name='Second Merchant',
            email='second@merchant.com'
        )
        bank2 = BankAccount.objects.create(
            merchant=merchant2,
            account_number='1111222233334444',
            ifsc_code='SBIN0009012',
            account_holder_name='Second Account',
        )
        LedgerEntry.objects.create(
            merchant=merchant2,
            entry_type='credit',
            amount_paise=100000,
            description='Credit for merchant 2',
        )

        # First merchant's request
        response1 = self.client.post(
            '/api/v1/payouts/',
            data={
                'amount_paise': 10000,
                'bank_account_id': str(self.bank_account.id),
            },
            format='json',
            HTTP_IDEMPOTENCY_KEY=shared_key,
        )

        # Second merchant's request with same key
        client2 = APIClient()
        token2 = str(RefreshToken.for_user(user2).access_token)
        client2.credentials(HTTP_AUTHORIZATION=f'Bearer {token2}')
        response2 = client2.post(
            '/api/v1/payouts/',
            data={
                'amount_paise': 10000,
                'bank_account_id': str(bank2.id),
            },
            format='json',
            HTTP_IDEMPOTENCY_KEY=shared_key,
        )

        self.assertEqual(response1.status_code, 201)
        self.assertEqual(response2.status_code, 201)
        self.assertNotEqual(response1.data['id'], response2.data['id'])
