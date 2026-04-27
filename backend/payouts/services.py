from django.db import models, transaction
from django.db.models import Sum, Q
from django.db.models.functions import Coalesce
from django.db.models import Value
from django.utils import timezone
from .models import Merchant, LedgerEntry, Payout, IdempotencyRecord


class InsufficientBalanceError(Exception):
    pass


class InvalidStateTransitionError(Exception):
    pass


def get_merchant_balance(merchant_id):
    """
    Returns a dict: { available_paise, held_paise, total_paise }

    Balance is calculated via DB aggregation - no Python math on fetched rows.
    """
    result = LedgerEntry.objects.filter(merchant_id=merchant_id).aggregate(
        total_credits=Coalesce(Sum('amount_paise', filter=Q(entry_type='credit')), Value(0)),
        total_debits=Coalesce(Sum('amount_paise', filter=Q(entry_type='debit')), Value(0)),
    )

    held = Payout.objects.filter(
        merchant_id=merchant_id,
        status__in=[Payout.Status.PENDING, Payout.Status.PROCESSING]
    ).aggregate(
        held=Coalesce(Sum('amount_paise'), Value(0))
    )['held']

    ledger_balance = result['total_credits'] - result['total_debits']

    return {
        'available_paise': ledger_balance - held,
        'held_paise': held,
        'total_paise': ledger_balance,
    }


def request_payout(merchant_id, amount_paise, bank_account_id, idempotency_key):
    """
    Creates a payout request. Uses select_for_update() to prevent race conditions.
    """
    with transaction.atomic():
        merchant = Merchant.objects.select_for_update().get(id=merchant_id)

        result = LedgerEntry.objects.filter(merchant_id=merchant_id).aggregate(
            total_credits=Coalesce(Sum('amount_paise', filter=Q(entry_type='credit')), Value(0)),
            total_debits=Coalesce(Sum('amount_paise', filter=Q(entry_type='debit')), Value(0)),
        )
        held = Payout.objects.filter(
            merchant_id=merchant_id,
            status__in=[Payout.Status.PENDING, Payout.Status.PROCESSING]
        ).aggregate(held=Coalesce(Sum('amount_paise'), Value(0)))['held']

        available = result['total_credits'] - result['total_debits'] - held

        if available < amount_paise:
            raise InsufficientBalanceError(f"Available: {available}, Requested: {amount_paise}")

        payout = Payout.objects.create(
            merchant_id=merchant_id,
            bank_account_id=bank_account_id,
            amount_paise=amount_paise,
            status=Payout.Status.PENDING,
            idempotency_key=idempotency_key,
        )

        return payout


LEGAL_TRANSITIONS = {
    Payout.Status.PENDING: [Payout.Status.PROCESSING],
    Payout.Status.PROCESSING: [Payout.Status.COMPLETED, Payout.Status.FAILED],
}


def transition_payout(payout, new_status):
    """Enforces state machine - only legal transitions allowed."""
    allowed = LEGAL_TRANSITIONS.get(payout.status, [])
    if new_status not in allowed:
        raise InvalidStateTransitionError(
            f"Cannot transition from {payout.status} to {new_status}"
        )
    payout.status = new_status

    if new_status == Payout.Status.PROCESSING:
        payout.processing_started_at = timezone.now()
    elif new_status == Payout.Status.COMPLETED:
        payout.completed_at = timezone.now()
    elif new_status == Payout.Status.FAILED:
        payout.failed_at = timezone.now()
    payout.save()


def complete_payout(payout_id):
    """Completes a payout - creates debit ledger entry."""
    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(id=payout_id)
        transition_payout(payout, Payout.Status.COMPLETED)

        LedgerEntry.objects.create(
            merchant=payout.merchant,
            entry_type=LedgerEntry.EntryType.DEBIT,
            amount_paise=payout.amount_paise,
            description=f'Payout {payout.id} to bank account {payout.bank_account_id}',
            payout=payout,
        )


def fail_payout(payout_id, reason):
    """Fails a payout - funds auto-released from held calculation."""
    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(id=payout_id)

        if payout.status not in [Payout.Status.PENDING, Payout.Status.PROCESSING]:
            raise InvalidStateTransitionError(
                f"Cannot fail payout in status {payout.status}"
            )

        payout.status = Payout.Status.FAILED
        payout.failed_at = timezone.now()
        payout.failure_reason = reason
        payout.save()