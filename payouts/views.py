from django.shortcuts import render
import uuid
from datetime import timedelta

from django.db import transaction, IntegrityError
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from merchants.models import Merchant, BankAccount
from ledger.models import LedgerEntry
from .models import Payout, IdempotencyKey
from .serializers import PayoutSerializer, PayoutRequestSerializer



@api_view(["GET"])
def merchant_payouts(request, merchant_id):
    try:
        Merchant.objects.get(id=merchant_id)
    except Merchant.DoesNotExist:
        return Response({"error": "Merchant not found"}, status=status.HTTP_404_NOT_FOUND)

    payouts = Payout.objects.filter(merchant_id=merchant_id)
    serializer = PayoutSerializer(payouts, many=True)
    return Response(serializer.data)


@api_view(["POST"])
def create_payout(request):
    serializer = PayoutRequestSerializer(data = request.data)
    if not serializer.is_valid():
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    idempotency_key = request.headers.get("idempotency-key")
    if not idempotency_key:
        return Response(
            {"error": "Idempotency-Key header is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        uuid.UUID(idempotency_key)
    except ValueError:
        return Response(
            {"error": "Idempotency-Key must be a valid UUID"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    merchant_id = serializer.validated_data["merchant_id"]
    existing_key = IdempotencyKey.objects.filter(
        key=idempotency_key,
        merchant_id=merchant_id,
        created_at__gte=timezone.now() - timedelta(hours=24),
    ).first()

    if existing_key:
        return Response(existing_key.response_body, status=existing_key.response_status)
    
    amount_paise = serializer.validated_data["amount_paise"]
    bank_account_id = serializer.validated_data["bank_account_id"]
    
    try:
        with transaction.atomic():
            try:
                merchant = Merchant.objects.select_for_update().get(id = merchant_id)
            except Merchant.DoesNotExist:
                return Response({"error": "Merchant not found"}, status=status.HTTP_404_NOT_FOUND)
            
            try:
                bank_account = BankAccount.objects.get(
                    id=bank_account_id, merchant=merchant
                )
            except BankAccount.DoesNotExist:
                return Response({"error": "Bank account not found for this merchant"}, status=status.HTTP_404_NOT_FOUND)
            
            balance = LedgerEntry.calculateBalance(merchant_id)
            available = balance["available_balance"]

            if amount_paise > available:
                error_response = {"error": "Insufficient balance"}
                error_status = status.HTTP_400_BAD_REQUEST

                IdempotencyKey.objects.create(
                    key=idempotency_key,
                    merchant=merchant,
                    response_status=error_status,
                    response_body=error_response,
                )

                return Response(error_response, status=error_status)
            
            payout = Payout.objects.create(
                merchant=merchant,
                bank_account=bank_account,
                amount_paise=amount_paise,
                status=Payout.Status.PENDING,
            )

            LedgerEntry.objects.create(
                merchant=merchant,
                entry_type=LedgerEntry.EntryType.DEBIT_HOLD,
                amount_paise=amount_paise,
                payout=payout,
                description=f"Hold for payout {payout.id}",
            )

            success_body = PayoutSerializer(payout).data
            success_status = status.HTTP_201_CREATED

            IdempotencyKey.objects.create(
                key=idempotency_key,
                merchant=merchant,
                payout=payout,
                response_status=success_status,
                response_body=success_body,
            )
    except IntegrityError:
        existing_key = IdempotencyKey.objects.filter(
            key=idempotency_key,
            merchant_id=merchant_id,
        ).first()

        if existing_key:
            return Response(existing_key.response_body, status=existing_key.response_status)

        return Response(
            {"error": "Request conflict, please retry"},
            status=status.HTTP_409_CONFLICT,
        )
    except Exception as e:
        print(f"ERROR: {e}")
        return Response(
            {"error": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    from .tasks import process_payout
    process_payout.delay(str(payout.id))

    return Response(success_body, status=success_status)       
