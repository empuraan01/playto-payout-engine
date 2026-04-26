# payouts/tests.py
import uuid
import threading
from django.test import TestCase, TransactionTestCase
from django.db import connection
from rest_framework.test import APIClient
from merchants.models import Merchant, BankAccount
from ledger.models import LedgerEntry
from .models import Payout, IdempotencyKey, PayoutAuditLog


class PayoutAPITests(TestCase):
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
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=10000000,
        )
        self.merchant2 = Merchant.objects.create(
            name="Other Merchant",
            email="other@merchant.com",
        )
        self.bank_account2 = BankAccount.objects.create(
            merchant=self.merchant2,
            account_holder_name="Other Account",
            account_number="9876543210",
            ifsc_code="TEST0005678",
        )
        LedgerEntry.objects.create(
            merchant=self.merchant2,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=10000000,
        )

    def _post_payout(self, merchant_id, amount_paise, bank_account_id, idempotency_key=None):
        if idempotency_key is None:
            idempotency_key = str(uuid.uuid4())
        return self.client.post(
            "/api/v1/payouts/",
            {
                "merchant_id": str(merchant_id),
                "amount_paise": amount_paise,
                "bank_account_id": str(bank_account_id),
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY=idempotency_key,
        )

    # --- Success ---
    def test_successful_payout_returns_201(self):
        response = self._post_payout(self.merchant.id, 1000000, self.bank_account.id)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["amount_paise"], 1000000)
        self.assertEqual(response.data["status"], "pending")

    def test_successful_payout_creates_debit_hold(self):
        self._post_payout(self.merchant.id, 1000000, self.bank_account.id)
        hold = LedgerEntry.objects.filter(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.DEBIT_HOLD,
        ).first()
        self.assertIsNotNone(hold)
        self.assertEqual(hold.amount_paise, 1000000)

    def test_successful_payout_reduces_available_balance(self):
        self._post_payout(self.merchant.id, 3000000, self.bank_account.id)
        balance = LedgerEntry.calculateBalance(self.merchant.id)
        self.assertEqual(balance["available_balance"], 7000000)
        self.assertEqual(balance["held_balance"], 3000000)

    # --- Validation errors ---
    def test_missing_idempotency_key_returns_400(self):
        response = self.client.post(
            "/api/v1/payouts/",
            {
                "merchant_id": str(self.merchant.id),
                "amount_paise": 1000000,
                "bank_account_id": str(self.bank_account.id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_idempotency_key_returns_400(self):
        response = self.client.post(
            "/api/v1/payouts/",
            {
                "merchant_id": str(self.merchant.id),
                "amount_paise": 1000000,
                "bank_account_id": str(self.bank_account.id),
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY="not-a-uuid",
        )
        self.assertEqual(response.status_code, 400)

    def test_insufficient_balance_returns_400(self):
        response = self._post_payout(self.merchant.id, 99999999, self.bank_account.id)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Insufficient", response.data["error"])

    def test_invalid_merchant_returns_404(self):
        response = self._post_payout(uuid.uuid4(), 1000000, self.bank_account.id)
        self.assertEqual(response.status_code, 404)

    def test_invalid_bank_account_returns_404(self):
        response = self._post_payout(self.merchant.id, 1000000, uuid.uuid4())
        self.assertIn(response.status_code, [400, 404])

    def test_bank_account_wrong_merchant_returns_error(self):
        response = self._post_payout(self.merchant.id, 1000000, self.bank_account2.id)
        self.assertIn(response.status_code, [400, 404])

    # --- Idempotency ---
    def test_same_key_same_merchant_returns_cached_response(self):
        key = str(uuid.uuid4())
        response1 = self._post_payout(self.merchant.id, 1000000, self.bank_account.id, key)
        response2 = self._post_payout(self.merchant.id, 1000000, self.bank_account.id, key)
        self.assertEqual(response1.status_code, 201)
        self.assertEqual(response2.status_code, 201)
        self.assertEqual(response1.data["id"], response2.data["id"])
        self.assertEqual(Payout.objects.filter(merchant=self.merchant).count(), 1)

    def test_same_key_different_merchant_creates_separate_payouts(self):
        key = str(uuid.uuid4())
        response1 = self._post_payout(self.merchant.id, 1000000, self.bank_account.id, key)
        response2 = self._post_payout(self.merchant2.id, 1000000, self.bank_account2.id, key)
        self.assertEqual(response1.status_code, 201)
        self.assertEqual(response2.status_code, 201)
        self.assertNotEqual(response1.data["id"], response2.data["id"])

    def test_insufficient_balance_cached_by_idempotency(self):
        key = str(uuid.uuid4())
        response1 = self._post_payout(self.merchant.id, 99999999, self.bank_account.id, key)
        response2 = self._post_payout(self.merchant.id, 99999999, self.bank_account.id, key)
        self.assertEqual(response1.status_code, 400)
        self.assertEqual(response2.status_code, 400)
        self.assertEqual(
            IdempotencyKey.objects.filter(key=key, merchant=self.merchant).count(), 1
        )


class PayoutConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.merchant = Merchant.objects.create(
            name="Concurrency Merchant",
            email="concurrent@merchant.com",
        )
        self.bank_account = BankAccount.objects.create(
            merchant=self.merchant,
            account_holder_name="Test Account",
            account_number="1234567890",
            ifsc_code="TEST0001234",
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=1000000,
        )

    def test_concurrent_payouts_only_one_succeeds(self):
        results = []

        def make_payout():
            try:
                client = APIClient()
                response = client.post(
                    "/api/v1/payouts/",
                    {
                        "merchant_id": str(self.merchant.id),
                        "amount_paise": 600000,
                        "bank_account_id": str(self.bank_account.id),
                    },
                    format="json",
                    HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
                )
                results.append(response.status_code)
            finally:
                connection.close()

        thread1 = threading.Thread(target=make_payout)
        thread2 = threading.Thread(target=make_payout)

        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()

        self.assertEqual(sorted(results), [201, 400])
        self.assertEqual(Payout.objects.filter(merchant=self.merchant).count(), 1)

        balance = LedgerEntry.calculateBalance(self.merchant.id)
        self.assertEqual(balance["available_balance"], 400000)
        self.assertEqual(balance["held_balance"], 600000)


class PayoutStateMachineTests(TestCase):
    def setUp(self):
        self.merchant = Merchant.objects.create(
            name="State Merchant",
            email="state@merchant.com",
        )
        self.bank_account = BankAccount.objects.create(
            merchant=self.merchant,
            account_holder_name="Test Account",
            account_number="1234567890",
            ifsc_code="TEST0001234",
        )

    def _create_payout(self, status=Payout.Status.PENDING):
        return Payout.objects.create(
            merchant=self.merchant,
            bank_account=self.bank_account,
            amount_paise=1000000,
            status=status,
        )

    def test_pending_to_processing(self):
        payout = self._create_payout()
        payout.transition_to(Payout.Status.PROCESSING)
        self.assertEqual(payout.status, Payout.Status.PROCESSING)

    def test_processing_to_completed(self):
        payout = self._create_payout(Payout.Status.PROCESSING)
        payout.transition_to(Payout.Status.COMPLETED)
        self.assertEqual(payout.status, Payout.Status.COMPLETED)

    def test_processing_to_failed(self):
        payout = self._create_payout(Payout.Status.PROCESSING)
        payout.transition_to(Payout.Status.FAILED)
        self.assertEqual(payout.status, Payout.Status.FAILED)

    def test_completed_to_pending_raises(self):
        payout = self._create_payout(Payout.Status.COMPLETED)
        with self.assertRaises(ValueError):
            payout.transition_to(Payout.Status.PENDING)

    def test_completed_to_failed_raises(self):
        payout = self._create_payout(Payout.Status.COMPLETED)
        with self.assertRaises(ValueError):
            payout.transition_to(Payout.Status.FAILED)

    def test_failed_to_completed_raises(self):
        payout = self._create_payout(Payout.Status.FAILED)
        with self.assertRaises(ValueError):
            payout.transition_to(Payout.Status.COMPLETED)

    def test_failed_to_pending_raises(self):
        payout = self._create_payout(Payout.Status.FAILED)
        with self.assertRaises(ValueError):
            payout.transition_to(Payout.Status.PENDING)

    def test_pending_to_completed_skipping_processing_raises(self):
        payout = self._create_payout()
        with self.assertRaises(ValueError):
            payout.transition_to(Payout.Status.COMPLETED)

    def test_transition_creates_audit_log(self):
        payout = self._create_payout()
        payout.transition_to(Payout.Status.PROCESSING, reason="Test transition")
        log = PayoutAuditLog.objects.filter(payout=payout).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.from_status, Payout.Status.PENDING)
        self.assertEqual(log.to_status, Payout.Status.PROCESSING)
        self.assertEqual(log.reason, "Test transition")