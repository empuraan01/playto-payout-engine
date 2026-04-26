from celery import shared_task
import random
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

@shared_task
def process_payout(payout_id):
    from .models import Payout
    from ledger.models import LedgerEntry

    try:
        payout = Payout.objects.get(id = payout_id)
    except Payout.DoesNotExist:
        return
    
    if payout.status != Payout.Status.PENDING and payout.status != Payout.Status.PROCESSING:
        return
    
    if payout.status == Payout.Status.PENDING:
        payout.transition_to(Payout.Status.PROCESSING, reason="Picked up by worker")
        payout.attempts += 1
        payout.last_attempted_at = timezone.now()
        payout.save(update_fields=["attempts", "last_attempted_at"])
    
    outcome = random.random()

    if outcome < 0.7:
        with transaction.atomic():
            payout.transition_to(Payout.Status.COMPLETED, reason="Bank settlement confirmed")
            LedgerEntry.objects.create(
                merchant=payout.merchant,
                entry_type=LedgerEntry.EntryType.DEBIT_CONFIRM,
                amount_paise=payout.amount_paise,
                payout=payout,
                description=f"Payout {payout.id} completed",
            )

    elif outcome < 0.9:
        with transaction.atomic():
            payout.transition_to(Payout.Status.FAILED, reason="Bank settlement rejected")
            LedgerEntry.objects.create(
                merchant=payout.merchant,
                entry_type=LedgerEntry.EntryType.DEBIT_RELEASE,
                amount_paise=payout.amount_paise,
                payout=payout,
                description=f"Payout {payout.id} failed, funds returned",
            )

    else:
        pass


@shared_task
def retry_stuck_payouts():
    from .models import Payout
    from ledger.models import LedgerEntry

    stuck_payouts = Payout.objects.filter(
        status=Payout.Status.PROCESSING,
        last_attempted_at__lte=timezone.now() - timedelta(seconds=30),
    )

    for payout in stuck_payouts:
        backoff_seconds = 30 * (2 ** (payout.attempts - 1))
        if payout.last_attempted_at and (timezone.now() - payout.last_attempted_at).total_seconds() < backoff_seconds:
            continue
        if payout.attempts >= 3:
            with transaction.atomic():
                payout.transition_to(
                    Payout.Status.FAILED,
                    reason=f"Max retries ({payout.attempts}) exceeded",
                )
                LedgerEntry.objects.create(
                    merchant=payout.merchant,
                    entry_type=LedgerEntry.EntryType.DEBIT_RELEASE,
                    amount_paise=payout.amount_paise,
                    payout=payout,
                    description=f"Payout {payout.id} failed after {payout.attempts} attempts, funds returned",
                )
        else:
            payout.attempts += 1
            payout.last_attempted_at = timezone.now()
            payout.save(update_fields=["attempts", "last_attempted_at"])
            process_payout.delay(str(payout.id))
