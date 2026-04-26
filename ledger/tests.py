# ledger/tests.py
import uuid
from django.test import TestCase
from rest_framework.test import APIClient
from merchants.models import Merchant, BankAccount
from ledger.models import LedgerEntry
from payouts.models import Payout


class LedgerBalanceTests(TestCase):
    def setUp(self):
        self.merchant = Merchant.objects.create(
            name="Test Merchant",
            email="test@merchant.com",
        )
        self.bank_account = BankAccount.objects.create(
            merchant=self.merchant,
            account_holder_name="Test Account",
            account_number="1234567890",
            ifsc_code="TEST0001234",
        )

    def test_no_entries_returns_zero(self):
        balance = LedgerEntry.calculateBalance(self.merchant.id)
        self.assertEqual(balance["available_balance"], 0)
        self.assertEqual(balance["held_balance"], 0)

    def test_credits_only(self):
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=5000000,
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=3000000,
        )
        balance = LedgerEntry.calculateBalance(self.merchant.id)
        self.assertEqual(balance["available_balance"], 8000000)
        self.assertEqual(balance["held_balance"], 0)

    def test_credit_and_hold(self):
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=5000000,
        )
        payout = Payout.objects.create(
            merchant=self.merchant,
            bank_account=self.bank_account,
            amount_paise=2000000,
            status=Payout.Status.PENDING,
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.DEBIT_HOLD,
            amount_paise=2000000,
            payout=payout,
        )
        balance = LedgerEntry.calculateBalance(self.merchant.id)
        self.assertEqual(balance["available_balance"], 3000000)
        self.assertEqual(balance["held_balance"], 2000000)

    def test_completed_payout(self):
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=5000000,
        )
        payout = Payout.objects.create(
            merchant=self.merchant,
            bank_account=self.bank_account,
            amount_paise=2000000,
            status=Payout.Status.COMPLETED,
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.DEBIT_HOLD,
            amount_paise=2000000,
            payout=payout,
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.DEBIT_CONFIRM,
            amount_paise=2000000,
            payout=payout,
        )
        balance = LedgerEntry.calculateBalance(self.merchant.id)
        self.assertEqual(balance["available_balance"], 3000000)
        self.assertEqual(balance["held_balance"], 0)

    def test_failed_payout_returns_funds(self):
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=5000000,
        )
        payout = Payout.objects.create(
            merchant=self.merchant,
            bank_account=self.bank_account,
            amount_paise=2000000,
            status=Payout.Status.FAILED,
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.DEBIT_HOLD,
            amount_paise=2000000,
            payout=payout,
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.DEBIT_RELEASE,
            amount_paise=2000000,
            payout=payout,
        )
        balance = LedgerEntry.calculateBalance(self.merchant.id)
        self.assertEqual(balance["available_balance"], 5000000)
        self.assertEqual(balance["held_balance"], 0)

    def test_multiple_payouts_mixed_states(self):
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=10000000,
        )
        payout1 = Payout.objects.create(
            merchant=self.merchant,
            bank_account=self.bank_account,
            amount_paise=3000000,
            status=Payout.Status.COMPLETED,
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.DEBIT_HOLD,
            amount_paise=3000000,
            payout=payout1,
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.DEBIT_CONFIRM,
            amount_paise=3000000,
            payout=payout1,
        )
        payout2 = Payout.objects.create(
            merchant=self.merchant,
            bank_account=self.bank_account,
            amount_paise=2000000,
            status=Payout.Status.PROCESSING,
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.DEBIT_HOLD,
            amount_paise=2000000,
            payout=payout2,
        )
        balance = LedgerEntry.calculateBalance(self.merchant.id)
        self.assertEqual(balance["available_balance"], 5000000)
        self.assertEqual(balance["held_balance"], 2000000)

    def test_balance_isolated_per_merchant(self):
        merchant2 = Merchant.objects.create(
            name="Other Merchant",
            email="other@merchant.com",
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=5000000,
        )
        LedgerEntry.objects.create(
            merchant=merchant2,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=9000000,
        )
        balance1 = LedgerEntry.calculateBalance(self.merchant.id)
        balance2 = LedgerEntry.calculateBalance(merchant2.id)
        self.assertEqual(balance1["available_balance"], 5000000)
        self.assertEqual(balance2["available_balance"], 9000000)


class LedgerAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.merchant = Merchant.objects.create(
            name="Test Merchant",
            email="test@merchant.com",
        )
        self.bank_account = BankAccount.objects.create(
            merchant=self.merchant,
            account_holder_name="Test Account",
            account_number="1234567890",
            ifsc_code="TEST0001234",
        )

    def test_balance_endpoint_returns_correct_values(self):
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=5000000,
        )
        response = self.client.get(f"/api/v1/merchants/{self.merchant.id}/balance/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["available_balance"], 5000000)
        self.assertEqual(response.data["held_balance"], 0)

    def test_balance_endpoint_invalid_merchant_returns_404(self):
        response = self.client.get(f"/api/v1/merchants/{uuid.uuid4()}/balance/")
        self.assertEqual(response.status_code, 404)

    def test_ledger_endpoint_returns_entries(self):
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=5000000,
            description="Payment from Client A",
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=3000000,
            description="Payment from Client B",
        )
        response = self.client.get(f"/api/v1/merchants/{self.merchant.id}/ledger/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_ledger_endpoint_invalid_merchant_returns_404(self):
        response = self.client.get(f"/api/v1/merchants/{uuid.uuid4()}/ledger/")
        self.assertEqual(response.status_code, 404)

    def test_ledger_endpoint_returns_newest_first(self):
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=1000000,
            description="First",
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=2000000,
            description="Second",
        )
        response = self.client.get(f"/api/v1/merchants/{self.merchant.id}/ledger/")
        self.assertEqual(response.data[0]["description"], "Second")
        self.assertEqual(response.data[1]["description"], "First")

    def test_ledger_entries_isolated_per_merchant(self):
        merchant2 = Merchant.objects.create(
            name="Other Merchant",
            email="other@merchant.com",
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=5000000,
        )
        LedgerEntry.objects.create(
            merchant=merchant2,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=9000000,
        )
        response = self.client.get(f"/api/v1/merchants/{self.merchant.id}/ledger/")
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["amount_paise"], 5000000)


class MerchantAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_merchant_list_returns_all(self):
        Merchant.objects.create(name="Merchant A", email="a@test.com")
        Merchant.objects.create(name="Merchant B", email="b@test.com")
        response = self.client.get("/api/v1/merchants/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_merchant_list_includes_bank_accounts(self):
        merchant = Merchant.objects.create(name="Merchant A", email="a@test.com")
        BankAccount.objects.create(
            merchant=merchant,
            account_holder_name="Account Holder",
            account_number="1234567890",
            ifsc_code="TEST0001234",
        )
        response = self.client.get("/api/v1/merchants/")
        self.assertEqual(len(response.data[0]["bank_accounts"]), 1)

    def test_merchant_list_empty(self):
        response = self.client.get("/api/v1/merchants/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)