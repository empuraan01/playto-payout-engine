from django.db import models
from django.db.models import Sum, Case, When, Value, BigIntegerField, F
import uuid


class LedgerEntry(models.Model):
    class EntryType(models.TextChoices):
        CREDIT = "credit"
        DEBIT_HOLD = "debit_hold"
        DEBIT_CONFIRM = "debit_confirm"
        DEBIT_RELEASE = "debit_release"

    id = models.UUIDField(primary_key=True, default = uuid.uuid4, editable = False)
    merchant = models.ForeignKey(
        "merchants.Merchant",
        on_delete=models.PROTECT,
        related_name="ledger_entries"
    )
    entry_type = models.CharField(max_length=20, choices=EntryType.choices)
    amount_paise = models.BigIntegerField()
    payout = models.ForeignKey(
        "payouts.Payout",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ledger_entries",
    )
    description = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

@staticmethod
def calculateBalance(merchant_id):
    result = LedgerEntry.objects.filter(
        merchant_id=merchant_id
    ).aggregate(
        available=Sum(
            Case(
                When(entry_type=LedgerEntry.EntryType.CREDIT, then=F("amount_paise")),
                When(entry_type=LedgerEntry.EntryType.DEBIT_RELEASE, then=F("amount_paise")),
                When(entry_type=LedgerEntry.EntryType.DEBIT_HOLD, then=Value(-1) * F("amount_paise")),
                default=Value(0),
                output_field=BigIntegerField(),
            )
        ),
        held=Sum(
            Case(
                When(entry_type=LedgerEntry.EntryType.DEBIT_HOLD, then= F("amount_paise")),
                When(entry_type=LedgerEntry.EntryType.DEBIT_CONFIRM, then= Value(-1) * F("amount_paise")),
                When(entry_type=LedgerEntry.EntryType.DEBIT_RELEASE, then= Value(-1) * F("amount_paise")),
                default=Value(0),
                output_field=BigIntegerField(),
            )
        ),
    )
    return {
        "available_balance": result["available"] or 0,
        "held_balance": result["held"] or 0,
    }

