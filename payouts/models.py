from django.db import models
import uuid

class Payout(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        PROCESSING = "processing"
        COMPLETED = "completed"
        FAILED = "failed"
    

    VALID_TRANSITIONS = {
        Status.PENDING: [Status.PROCESSING],
        Status.PROCESSING: [Status.COMPLETED, Status.FAILED],
        Status.COMPLETED: [],
        Status.FAILED: [],
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        "merchants.Merchant",
        on_delete=models.PROTECT,
        related_name="payouts",
    )
    bank_account = models.ForeignKey(
        "merchants.BankAccount",
        on_delete=models.PROTECT,
        related_name="payouts",
    )
    amount_paise = models.BigIntegerField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    attempts = models.IntegerField(default=0)
    last_attempted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def transition_to(self, new_status, reason = ""):
        if new_status not in self.VALID_TRANSITIONS[self.status]:
            raise ValueError(
                f"Invalid transition: {self.status} → {new_status}"
            )
        old_status = self.status
        self.status = new_status
        self.save(update_fields=["status", "updated_at"])

        PayoutAuditLog.objects.create(
        payout=self,
        from_status=old_status,
        to_status=new_status,
        reason=reason,
    )

    def __str__(self):
        return f"Payout {self.id} | {self.amount_paise}p | {self.status}"
    

class IdempotencyKey(models.Model):
    key = models.UUIDField()
    merchant = models.ForeignKey(
        "merchants.Merchant",
        on_delete=models.PROTECT,
        related_name="idempotency_keys",
    )
    response_status = models.IntegerField()
    response_body = models.JSONField()
    payout = models.ForeignKey(
        Payout,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="idempotency_keys",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["key", "merchant"],
                name="unique_key_per_merchant",
            )
        ]

    def __str__(self):
        return f"{self.key} | {self.merchant}"



class PayoutAuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payout = models.ForeignKey(
        Payout,
        on_delete=models.PROTECT,
        related_name="audit_logs",
    )
    from_status = models.CharField(max_length=20, choices=Payout.Status.choices)
    to_status = models.CharField(max_length=20, choices=Payout.Status.choices)
    reason = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.payout_id} | {self.from_status} → {self.to_status}"
