"""
Concurrency Test:
Verifies that two simultaneous payout requests from the same merchant
cannot overdraw the balance. Given a merchant with ₹100 balance,
two concurrent ₹60 requests should result in exactly one success
and one rejection.

This test uses threading to simulate true concurrent API calls.
The SELECT FOR UPDATE lock in the payout creation view ensures
that the second transaction blocks until the first commits,
preventing the classic check-then-deduct race condition.
"""
import uuid
import threading
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from payouts.models import Merchant, BankAccount, LedgerEntry, Payout


class ConcurrencyTest(TransactionTestCase):
    """
    Uses TransactionTestCase (not TestCase) because we need real
    database transactions — TestCase wraps everything in a single
    transaction which defeats the purpose of testing SELECT FOR UPDATE.
    """

    def setUp(self):
        """Create a merchant with exactly ₹100 (10000 paise) balance."""
        self.user = User.objects.create_user(
            username='concurrency_test_user',
            password='testpass123'
        )
        self.merchant = Merchant.objects.create(
            user=self.user,
            business_name='Concurrency Test Merchant',
            email='test@concurrent.com'
        )
        self.bank_account = BankAccount.objects.create(
            merchant=self.merchant,
            account_number='1234567890',
            ifsc_code='HDFC0001234',
            account_holder_name='Test Account',
            is_primary=True,
        )
        # Seed exactly ₹100 (10000 paise)
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type='credit',
            amount_paise=10000,
            description='Test credit - ₹100',
        )

        # Get JWT token
        refresh = RefreshToken.for_user(self.user)
        self.token = str(refresh.access_token)

    def test_concurrent_payouts_prevent_overdraft(self):
        """
        Two simultaneous ₹60 payouts from a ₹100 balance.
        Exactly one must succeed (201), exactly one must be rejected (422).
        Final available balance = ₹40 (with ₹60 held for the successful payout).
        """
        results = []
        errors = []

        def make_payout_request(idempotency_key):
            """Each thread uses its own APIClient instance."""
            try:
                client = APIClient()
                client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
                response = client.post(
                    '/api/v1/payouts/',
                    data={
                        'amount_paise': 6000,  # ₹60
                        'bank_account_id': str(self.bank_account.id),
                    },
                    format='json',
                    HTTP_IDEMPOTENCY_KEY=idempotency_key,
                )
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))

        # Launch two threads simultaneously
        key1 = str(uuid.uuid4())
        key2 = str(uuid.uuid4())
        t1 = threading.Thread(target=make_payout_request, args=(key1,))
        t2 = threading.Thread(target=make_payout_request, args=(key2,))

        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        # Assertions
        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")
        self.assertEqual(len(results), 2, "Both requests should complete")

        # Exactly one 201 (created) and one 422 (insufficient funds)
        self.assertIn(201, results, "One request should succeed with 201")
        self.assertIn(422, results, "One request should fail with 422")
        self.assertEqual(results.count(201), 1, "Exactly one success")
        self.assertEqual(results.count(422), 1, "Exactly one rejection")

        # Only one payout should exist in DB
        payouts = Payout.objects.filter(merchant=self.merchant)
        self.assertEqual(payouts.count(), 1, "Only one payout should be created")

        # Balance check: ₹100 - ₹60 (held) = ₹40 available
        from payouts.views import get_merchant_balance
        balance = get_merchant_balance(self.merchant)
        self.assertEqual(
            balance['available_balance_paise'], 4000,
            f"Available balance should be 4000 paise (₹40), got {balance['available_balance_paise']}"
        )
        self.assertEqual(
            balance['held_balance_paise'], 6000,
            f"Held balance should be 6000 paise (₹60), got {balance['held_balance_paise']}"
        )
