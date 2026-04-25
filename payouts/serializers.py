from rest_framework import serializers
from .models import Payout


class PayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payout
        fields = ["id", "merchant", "bank_account", "amount_paise", "status", "attempts", "created_at", "updated_at"]


class PayoutRequestSerializer(serializers.Serializer):
    merchant_id = serializers.UUIDField()
    amount_paise = serializers.IntegerField(min_value=1)
    bank_account_id = serializers.UUIDField()