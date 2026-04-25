from django.urls import path, include

urlpatterns = [
    path("api/merchants/", include("merchants.urls")),
    path("api/ledger/", include("ledger.urls")),
    path("api/payouts/", include("payouts.urls")),
]
