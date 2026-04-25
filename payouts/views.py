from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from merchants.models import Merchant
from .models import Payout
from .serializers import PayoutSerializer


@api_view(["GET"])
def merchant_payouts(request, merchant_id):
    try:
        Merchant.objects.get(id=merchant_id)
    except Merchant.DoesNotExist:
        return Response({"error": "Merchant not found"}, status=status.HTTP_404_NOT_FOUND)

    payouts = Payout.objects.filter(merchant_id=merchant_id)
    serializer = PayoutSerializer(payouts, many=True)
    return Response(serializer.data)
