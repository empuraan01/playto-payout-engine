from django.shortcuts import render
from rest_framework import status   
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Merchant
from .serializers import MerchantSerializer
from ledger.models import LedgerEntry
from ledger.serializers import LedgerEntrySerializer

@api_view(["GET"])
def merchant_list(request):
    merchants = Merchant.objects.prefetch_related("bank_accounts").all()
    serializer = MerchantSerializer(merchants, many=True)
    return Response(serializer.data)

@api_view(["GET"])
def merchant_balance(request, merchant_id):
    try:
        Merchant.objects.get(id=merchant_id)
    except Merchant.DoesNotExist:
        return Response({"error": "Merchant not found"}, status=status.HTTP_404_NOT_FOUND)

    balance = LedgerEntry.calculateBalance(merchant_id)
    return Response(balance)


@api_view(["GET"])
def merchant_ledger(request, merchant_id):
    try:
        Merchant.objects.get(id=merchant_id)
    except Merchant.DoesNotExist:
        return Response({"error": "Merchant not found"}, status=status.HTTP_404_NOT_FOUND)

    entries = LedgerEntry.objects.filter(merchant_id=merchant_id)
    serializer = LedgerEntrySerializer(entries, many=True)
    return Response(serializer.data)



