from django.db import models
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



