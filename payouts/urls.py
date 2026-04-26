from django.urls import path
from . import views

urlpatterns = [
    path("<uuid:merchant_id>/", views.merchant_payouts, name="merchant-payouts"),
    path("", views.create_payout, name="create-payout")
]
