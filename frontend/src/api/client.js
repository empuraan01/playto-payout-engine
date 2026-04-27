import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api/v1",
});

export function fetchMerchants() {
  return api.get("/merchants/");
}

export function fetchBalance(merchantId) {
  return api.get(`/merchants/${merchantId}/balance/`);
}

export function fetchLedger(merchantId) {
  return api.get(`/merchants/${merchantId}/ledger/`);
}

export function fetchPayouts(merchantId) {
  return api.get(`/payouts/${merchantId}/`);
}

export function createPayout(merchantId, amountPaise, bankAccountId, idempotencyKey) {
  return api.post(
    "/payouts/",
    {
      merchant_id: merchantId,
      amount_paise: amountPaise,
      bank_account_id: bankAccountId,
    },
    {
      headers: { "Idempotency-Key": idempotencyKey },
    }
  );
}


export default api;