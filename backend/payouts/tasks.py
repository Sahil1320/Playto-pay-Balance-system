import random
import logging
from datetime import timedelta
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

logger = logging.getLogger('payouts')


def simulate_bank_settlement():
    """
    Simulates bank API response.
    Returns: 'success' (70%), 'failed' (20%), 'hang' (10%)
    """
    roll = random.random()
    if roll < 0.70:
        return 'success'
    elif roll < 0.90:
        return 'failed'
    else:
        return 'hang'


@shared_task(bind=True, max_retries=0)
def process_payout(self, payout_id):
    """
    Process a single payout through the bank settlement simulation.
    
    Lifecycle:
    1. Transition pending → processing (with lock)
    2. Simulate bank settlement OUTSIDE the transaction (don't hold locks during I/O)
    3. On success: processing → completed, create debit+release entries
    4. On failure: processing → failed, release held funds
    5. On hang: do nothing, retry_stuck_payouts will pick it up
    """
    from .models import Payout, LedgerEntry

    logger.info(f"Processing payout {payout_id}")

    # --- Step 1: Transition to processing ---
    with transaction.atomic():
        try:
            payout = Payout.objects.select_for_update().get(id=payout_id)
        except Payout.DoesNotExist:
            logger.error(f"Payout {payout_id} not found")
            return

        if payout.status not in ('pending', 'processing'):
            logger.info(f"Payout {payout_id} already in terminal state: {payout.status}")
            return

        if payout.status == 'pending':
            payout.transition_to('processing')

        payout.attempts += 1
        payout.last_attempted_at = timezone.now()
        payout.save()

    # --- Step 2: Simulate bank settlement OUTSIDE transaction ---
    # We do NOT hold any DB lock while waiting for the "bank API"
    result = simulate_bank_settlement()
    logger.info(f"Payout {payout_id} attempt #{payout.attempts} result: {result}")

    if result == 'success':
        # --- Step 3a: Mark completed + finalize ledger ---
        with transaction.atomic():
            payout = Payout.objects.select_for_update().get(id=payout_id)
            if payout.status != 'processing':
                logger.warning(f"Payout {payout_id} state changed during processing: {payout.status}")
                return

            payout.transition_to('completed')
            payout.save()

            # Release the hold and create final debit — ATOMIC with state transition
            LedgerEntry.objects.create(
                merchant=payout.merchant,
                entry_type='release',
                amount_paise=payout.amount_paise,
                reference_id=payout.id,
                description=f'Hold released for completed payout {str(payout.id)[:8]}',
            )
            LedgerEntry.objects.create(
                merchant=payout.merchant,
                entry_type='debit',
                amount_paise=payout.amount_paise,
                reference_id=payout.id,
                description=f'Payout settled to bank {str(payout.id)[:8]}',
            )

        logger.info(f"Payout {payout_id} completed successfully")

    elif result == 'failed':
        # --- Step 3b: Mark failed + return funds ---
        with transaction.atomic():
            payout = Payout.objects.select_for_update().get(id=payout_id)
            if payout.status != 'processing':
                logger.warning(f"Payout {payout_id} state changed during processing: {payout.status}")
                return

            payout.transition_to('failed')
            payout.save()

            # Release held funds — merchant gets them back
            LedgerEntry.objects.create(
                merchant=payout.merchant,
                entry_type='release',
                amount_paise=payout.amount_paise,
                reference_id=payout.id,
                description=f'Funds returned — payout {str(payout.id)[:8]} failed',
            )

        logger.info(f"Payout {payout_id} failed — funds returned to merchant")

    else:
        # result == 'hang' — do nothing
        # retry_stuck_payouts periodic task will pick this up after 30 seconds
        logger.info(f"Payout {payout_id} simulating hang — will be retried")


@shared_task
def retry_stuck_payouts():
    """
    Periodic task (runs every 15s via Celery Beat).
    Finds payouts stuck in 'processing' for >30 seconds and retries them.
    
    Exponential backoff: wait increases with each attempt.
    Max 3 attempts, then move to failed and return funds.
    """
    from .models import Payout, LedgerEntry

    now = timezone.now()

    # Find payouts stuck in processing
    stuck_payouts = Payout.objects.filter(
        status='processing',
        last_attempted_at__isnull=False,
    )

    for payout in stuck_payouts:
        # Exponential backoff: 30s, 60s, 120s
        backoff_seconds = 30 * (2 ** (payout.attempts - 1))
        retry_after = payout.last_attempted_at + timedelta(seconds=backoff_seconds)

        if now < retry_after:
            continue  # Not time to retry yet

        if payout.attempts >= 3:
            # Max retries exceeded — fail the payout and return funds
            logger.warning(
                f"Payout {payout.id} exceeded max retries ({payout.attempts}). Moving to failed."
            )
            with transaction.atomic():
                p = Payout.objects.select_for_update().get(id=payout.id)
                if p.status != 'processing':
                    continue

                p.transition_to('failed')
                p.save()

                LedgerEntry.objects.create(
                    merchant=p.merchant,
                    entry_type='release',
                    amount_paise=p.amount_paise,
                    reference_id=p.id,
                    description=f'Max retries exceeded — funds returned for payout {str(p.id)[:8]}',
                )
        else:
            # Retry the payout
            logger.info(
                f"Retrying stuck payout {payout.id} (attempt {payout.attempts + 1}/3, "
                f"backoff={backoff_seconds}s)"
            )
            process_payout.delay(str(payout.id))


@shared_task
def cleanup_expired_idempotency_keys():
    """
    Periodic task to clean up idempotency keys older than 24 hours.
    Runs every hour via Celery Beat.
    """
    from .models import IdempotencyKey

    cutoff = timezone.now() - timedelta(hours=24)
    deleted_count, _ = IdempotencyKey.objects.filter(created_at__lt=cutoff).delete()
    if deleted_count:
        logger.info(f"Cleaned up {deleted_count} expired idempotency keys")
