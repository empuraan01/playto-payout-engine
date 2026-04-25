from django.urls import path
from . import views

urlpatterns = [
    path("", views.merchant_list, name="merchant-list"),
    path("<uuid:merchant_id>/balance/", views.merchant_balance, name="merchant-balance"),
    path("<uuid:merchant_id>/ledger/", views.merchant_ledger, name="merchant-ledger"),
]
