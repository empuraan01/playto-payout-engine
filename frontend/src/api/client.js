import axios from "axios";

const api = axios.create({
  baseURL: "/api/v1",
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

//todo : Create Payout Request


export default api;