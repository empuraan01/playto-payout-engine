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



