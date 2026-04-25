"""
Seed script: creates test merchants, bank accounts, and credit history.

Usage: python manage.py seed
"""

from django.core.management.base import BaseCommand
from merchants.models import Merchant, BankAccount
from ledger.models import LedgerEntry


class Command(BaseCommand):
    help = "Seed the database with test merchants and credit history"

    def handle(self, *args, **options):
        # Clear existing data (safe for dev only)
        LedgerEntry.objects.all().delete()
        BankAccount.objects.all().delete()
        Merchant.objects.all().delete()

        # --- Merchant 1: Acme Agency ---
        acme = Merchant.objects.create(
            name="Acme Agency",
            email="billing@acme.agency",
        )
        acme_bank = BankAccount.objects.create(
            merchant=acme,
            account_holder_name="Acme Agency Pvt Ltd",
            account_number="1234567890",
            ifsc_code="HDFC0001234",
        )
        # Credits: 3 customer payments totalling ₹1,50,000
        LedgerEntry.objects.create(
            merchant=acme,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=5000000,  # ₹50,000
            description="Payment from Client Alpha",
        )
        LedgerEntry.objects.create(
            merchant=acme,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=7500000,  # ₹75,000
            description="Payment from Client Beta",
        )
        LedgerEntry.objects.create(
            merchant=acme,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=2500000,  # ₹25,000
            description="Payment from Client Gamma",
        )

        # --- Merchant 2: Freelancer Priya ---
        priya = Merchant.objects.create(
            name="Priya Sharma",
            email="priya@freelancer.dev",
        )
        priya_bank = BankAccount.objects.create(
            merchant=priya,
            account_holder_name="Priya Sharma",
            account_number="9876543210",
            ifsc_code="ICIC0005678",
        )
        # Credits: 2 customer payments totalling ₹80,000
        LedgerEntry.objects.create(
            merchant=priya,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=5000000,  # ₹50,000
            description="Payment from US Startup Inc",
        )
        LedgerEntry.objects.create(
            merchant=priya,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=3000000,  # ₹30,000
            description="Payment from EU Design Co",
        )

        # --- Merchant 3: Nova Digital ---
        nova = Merchant.objects.create(
            name="Nova Digital",
            email="finance@novadigital.io",
        )
        nova_bank = BankAccount.objects.create(
            merchant=nova,
            account_holder_name="Nova Digital Solutions LLP",
            account_number="5555666677",
            ifsc_code="SBIN0009012",
        )
        # Credits: 2 customer payments totalling ₹2,00,000
        LedgerEntry.objects.create(
            merchant=nova,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=12000000,  # ₹1,20,000
            description="Payment from BigCorp LLC",
        )
        LedgerEntry.objects.create(
            merchant=nova,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=8000000,  # ₹80,000
            description="Payment from MegaTech GmbH",
        )

        self.stdout.write(self.style.SUCCESS(
            f"Seeded 3 merchants:\n"
            f"  Acme Agency     — ₹1,50,000 balance\n"
            f"  Priya Sharma    — ₹80,000 balance\n"
            f"  Nova Digital    — ₹2,00,000 balance\n"
        ))