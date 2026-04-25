from django.urls import path, include

urlpatterns = [
    path("api/v1/merchants/", include("merchants.urls")),
    path("api/ledger/", include("ledger.urls")),
    path("api/v1/payouts/", include("payouts.urls")),
]
