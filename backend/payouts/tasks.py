import random
from celery import shared_task
from django.db import transaction, OperationalError
from django.utils import timezone
from datetime import timedelta as dt_timedelta
from .models import Payout
from .services import complete_payout, fail_payout


@shared_task
def process_pending_payouts():
    """
    Picks up payouts in PENDING state and processes them.
    Runs every 10 seconds via Celery Beat.
    """
    pending_ids = list(
        Payout.objects.filter(status=Payout.Status.PENDING)
        .values_list('id', flat=True)[:10]
    )
    for payout_id in pending_ids:
        process_single_payout.delay(str(payout_id))


@shared_task(bind=True, max_retries=3)
def process_single_payout(self, payout_id):
    """
    Processes a single payout - moves to PROCESSING then simulates bank outcome.
    70% success, 20% fail, 10% hang (gets stuck).
    """
    with transaction.atomic():
        try:
            payout = Payout.objects.select_for_update(nowait=True).get(
                id=payout_id, status=Payout.Status.PENDING
            )
        except Payout.DoesNotExist:
            return
        except OperationalError:
            return

        payout.status = Payout.Status.PROCESSING
        payout.processing_started_at = timezone.now()
        payout.attempt_count += 1
        payout.save()

    outcome = random.choices(
        ['success', 'fail', 'hang'],
        weights=[70, 20, 10]
    )[0]

    if outcome == 'success':
        complete_payout(payout_id)
    elif outcome == 'fail':
        fail_payout(payout_id, reason='Bank declined the transaction')
    elif outcome == 'hang':
        pass


@shared_task
def retry_stuck_payouts():
    """
    Finds payouts stuck in PROCESSING for > 30 seconds.
    Retries up to 3 attempts, then fails them.
    Runs every 15 seconds via Celery Beat.
    """
    cutoff = timezone.now() - dt_timedelta(seconds=30)
    stuck_payouts = Payout.objects.filter(
        status=Payout.Status.PROCESSING,
        processing_started_at__lt=cutoff
    )

    for payout in stuck_payouts:
        if payout.attempt_count >= 3:
            fail_payout(payout.id, reason='Max retry attempts exceeded')
        else:
            with transaction.atomic():
                p = Payout.objects.select_for_update().get(id=payout.id)
                if p.status == Payout.Status.PROCESSING:
                    p.status = Payout.Status.PENDING
                    p.processing_started_at = None
                    p.save()