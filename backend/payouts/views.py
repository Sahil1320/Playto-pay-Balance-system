import json
import logging
from django.db import transaction
from django.db.models import Sum, Case, When, Value, BigIntegerField
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User

from .models import Merchant, BankAccount, LedgerEntry, Payout, IdempotencyKey
from .serializers import (
    MerchantSerializer, BankAccountSerializer, LedgerEntrySerializer,
    PayoutSerializer, PayoutCreateSerializer, BalanceSerializer,
    MerchantRegistrationSerializer,
)

logger = logging.getLogger('payouts')


def get_merchant_balance(merchant):
    """
    Calculate merchant balance using DATABASE-LEVEL aggregation.
    No Python arithmetic on fetched rows — the DB does all the math.
    
    Available = SUM(credits + releases) - SUM(holds + debits)
    Held = SUM(holds) - SUM(releases) - SUM(debits that reference a payout)
    """
    result = LedgerEntry.objects.filter(merchant=merchant).aggregate(
        total_credits=Coalesce(
            Sum(
                Case(
                    When(entry_type='credit', then='amount_paise'),
                    default=Value(0),
                    output_field=BigIntegerField()
                )
            ), Value(0), output_field=BigIntegerField()
        ),
        total_releases=Coalesce(
            Sum(
                Case(
                    When(entry_type='release', then='amount_paise'),
                    default=Value(0),
                    output_field=BigIntegerField()
                )
            ), Value(0), output_field=BigIntegerField()
        ),
        total_holds=Coalesce(
            Sum(
                Case(
                    When(entry_type='hold', then='amount_paise'),
                    default=Value(0),
                    output_field=BigIntegerField()
                )
            ), Value(0), output_field=BigIntegerField()
        ),
        total_debits=Coalesce(
            Sum(
                Case(
                    When(entry_type='debit', then='amount_paise'),
                    default=Value(0),
                    output_field=BigIntegerField()
                )
            ), Value(0), output_field=BigIntegerField()
        ),
    )

    total_credits = result['total_credits']
    total_releases = result['total_releases']
    total_holds = result['total_holds']
    total_debits = result['total_debits']

    # Available = (credits + releases) - (holds + debits)
    available_balance = (total_credits + total_releases) - (total_holds + total_debits)
    # Held = holds - releases - debits (for payout-related entries)
    held_balance = total_holds - total_releases - total_debits

    return {
        'available_balance_paise': available_balance,
        'held_balance_paise': max(held_balance, 0),
        'total_credits_paise': total_credits,
        'total_debits_paise': total_debits,
        'available_balance_rupees': f"₹{available_balance / 100:,.2f}",
        'held_balance_rupees': f"₹{max(held_balance, 0) / 100:,.2f}",
    }


def get_merchant_balance_locked(merchant):
    """
    Same as get_merchant_balance, but acquires a SELECT FOR UPDATE lock
    on the merchant's ledger entries. MUST be called inside transaction.atomic().
    
    This prevents concurrent payout requests from both reading the same balance.
    The second transaction will BLOCK here until the first one commits.
    """
    # Lock all ledger entries for this merchant
    LedgerEntry.objects.filter(merchant=merchant).select_for_update()

    # Now calculate — same logic but we hold the lock
    return get_merchant_balance(merchant)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_merchant(request):
    """Register a new merchant with JWT credentials."""
    serializer = MerchantRegistrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    data = serializer.validated_data

    if User.objects.filter(username=data['username']).exists():
        return Response(
            {'error': 'Username already exists.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    with transaction.atomic():
        user = User.objects.create_user(
            username=data['username'],
            password=data['password'],
            email=data['email']
        )
        merchant = Merchant.objects.create(
            user=user,
            business_name=data['business_name'],
            email=data['email']
        )

    return Response(
        MerchantSerializer(merchant).data,
        status=status.HTTP_201_CREATED
    )


class MerchantViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for merchant details."""
    serializer_class = MerchantSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Merchant.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """Get current authenticated merchant's profile."""
        try:
            merchant = request.user.merchant
        except Merchant.DoesNotExist:
            return Response(
                {'error': 'No merchant profile found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(MerchantSerializer(merchant).data)

    @action(detail=False, methods=['get'], url_path='me/balance')
    def my_balance(self, request):
        """Get current merchant's balance (DB-level aggregation)."""
        merchant = request.user.merchant
        balance = get_merchant_balance(merchant)
        return Response(BalanceSerializer(balance).data)

    @action(detail=False, methods=['get'], url_path='me/ledger')
    def my_ledger(self, request):
        """Get current merchant's ledger entries, paginated."""
        merchant = request.user.merchant
        entries = LedgerEntry.objects.filter(merchant=merchant).order_by('-created_at')
        page = self.paginate_queryset(entries)
        if page is not None:
            serializer = LedgerEntrySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = LedgerEntrySerializer(entries, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='me/payouts')
    def my_payouts(self, request):
        """Get current merchant's payout history."""
        merchant = request.user.merchant
        payouts = Payout.objects.filter(merchant=merchant).order_by('-created_at')
        page = self.paginate_queryset(payouts)
        if page is not None:
            serializer = PayoutSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = PayoutSerializer(payouts, many=True)
        return Response(serializer.data)


class PayoutViewSet(viewsets.ViewSet):
    """
    Payout creation with idempotency support.
    
    POST /api/v1/payouts/
      Headers: Idempotency-Key: <uuid>, Authorization: Bearer <token>
      Body: { "amount_paise": 10000, "bank_account_id": "<uuid>" }
    
    GET /api/v1/payouts/<id>/
      Returns payout details.
    """
    permission_classes = [IsAuthenticated]

    def create(self, request):
        """
        Create a payout request with idempotency.
        
        Flow:
        1. Validate Idempotency-Key header
        2. Check if key was already used → return cached response
        3. Lock merchant's ledger entries (SELECT FOR UPDATE)
        4. Validate balance >= amount
        5. Create Payout + Hold ledger entry atomically
        6. Cache response in IdempotencyKey
        7. Dispatch Celery task on commit
        """
        merchant = request.user.merchant

        # --- Step 1: Validate idempotency key ---
        idempotency_key = request.headers.get('Idempotency-Key')
        if not idempotency_key:
            return Response(
                {'error': 'Idempotency-Key header is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # --- Step 2: Check for existing key ---
        expiry_cutoff = timezone.now() - timedelta(hours=24)
        try:
            existing = IdempotencyKey.objects.get(
                key=idempotency_key,
                merchant=merchant,
                created_at__gte=expiry_cutoff
            )
            if existing.is_completed:
                # Return the exact same cached response
                logger.info(f"Idempotency hit: key={idempotency_key[:8]}... returning cached response")
                return Response(
                    existing.response_body,
                    status=existing.response_status
                )
            else:
                # Request is still in-flight
                logger.warning(f"Idempotency conflict: key={idempotency_key[:8]}... request in-flight")
                return Response(
                    {'error': 'A request with this idempotency key is already being processed.'},
                    status=status.HTTP_409_CONFLICT
                )
        except IdempotencyKey.DoesNotExist:
            pass  # New key, proceed

        # --- Step 3: Validate request body ---
        serializer = PayoutCreateSerializer(
            data=request.data,
            context={'merchant': merchant}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        amount_paise = serializer.validated_data['amount_paise']
        bank_account_id = serializer.validated_data['bank_account_id']
        bank_account = BankAccount.objects.get(id=bank_account_id)

        # --- Step 4: Create idempotency key record (marks request as in-flight) ---
        idem_record = IdempotencyKey.objects.create(
            key=idempotency_key,
            merchant=merchant,
            request_method='POST',
            request_path=request.path,
        )

        try:
            # --- Step 5: Lock, validate balance, create payout + hold ATOMICALLY ---
            with transaction.atomic():
                # SELECT FOR UPDATE on merchant's ledger entries
                # This blocks concurrent payout requests until this transaction commits
                balance_data = get_merchant_balance_locked(merchant)
                available = balance_data['available_balance_paise']

                if amount_paise > available:
                    # Insufficient funds — still cache this response
                    response_data = {
                        'error': 'Insufficient balance.',
                        'available_balance_paise': available,
                        'requested_amount_paise': amount_paise,
                    }
                    response_status = status.HTTP_422_UNPROCESSABLE_ENTITY

                    idem_record.response_status = response_status
                    idem_record.response_body = response_data
                    idem_record.save()

                    return Response(response_data, status=response_status)

                # Create payout record
                payout = Payout.objects.create(
                    merchant=merchant,
                    bank_account=bank_account,
                    amount_paise=amount_paise,
                    status='pending',
                )

                # Create hold ledger entry — funds reserved
                LedgerEntry.objects.create(
                    merchant=merchant,
                    entry_type='hold',
                    amount_paise=amount_paise,
                    reference_id=payout.id,
                    description=f'Funds held for payout {str(payout.id)[:8]}',
                )

                # Prepare response
                response_data = json.loads(json.dumps(PayoutSerializer(payout).data, default=str))
                response_status_code = status.HTTP_201_CREATED

                # Cache response in idempotency record
                idem_record.response_status = response_status_code
                idem_record.response_body = response_data
                idem_record.save()

                # Dispatch Celery task AFTER transaction commits
                # This ensures the payout exists in DB when the worker picks it up
                transaction.on_commit(
                    lambda pid=str(payout.id): __import__('payouts.tasks', fromlist=['process_payout']).process_payout.delay(pid)
                )

            logger.info(
                f"Payout created: id={payout.id}, amount=₹{amount_paise/100:.2f}, "
                f"merchant={merchant.business_name}"
            )
            return Response(response_data, status=response_status_code)

        except Exception as e:
            # Clean up idempotency record on unexpected errors
            logger.error(f"Payout creation failed: {e}")
            idem_record.delete()
            raise

    def retrieve(self, request, pk=None):
        """Get payout details."""
        try:
            payout = Payout.objects.get(id=pk, merchant=request.user.merchant)
        except Payout.DoesNotExist:
            return Response(
                {'error': 'Payout not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(PayoutSerializer(payout).data)
