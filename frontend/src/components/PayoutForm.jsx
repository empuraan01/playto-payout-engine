import { useState, useEffect } from "react";
import { createPayout } from "../api/client";

export default function PayoutForm({ merchant, onSuccess }) {
  const [amountRupees, setAmountRupees] = useState("");
  const [selectedBank, setSelectedBank] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    if (merchant?.bank_accounts?.length > 0) {
      setSelectedBank(merchant.bank_accounts[0].id);
    }
  }, [merchant]);

  const handleSubmit = async () => {
    if (!amountRupees || !selectedBank) return;

    setSubmitting(true);
    setMessage(null);

    const amountPaise = Math.round(parseFloat(amountRupees) * 100);
    const idempotencyKey = crypto.randomUUID();

    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        await createPayout(merchant.id, amountPaise, selectedBank, idempotencyKey);
        setMessage({ type: "success", text: "Payout requested successfully" });
        setAmountRupees("");
        onSuccess();
        break;
      } catch (err) {
        if (err.response) {
          // Server responded with an error (400, 404, etc) — don't retry
          const detail = err.response?.data?.error || "Something went wrong";
          setMessage({ type: "error", text: detail });
          break;
        }
        // Network error — retry with same key
        if (attempt === 2) {
          setMessage({ type: "error", text: "Network error, please try again" });
        }
      }
    }

    setSubmitting(false);
  };

  if (!merchant) return null;

  return (
    <div className="bg-zinc-900/50 border border-zinc-800/40 rounded-xl p-6">
      <h2 className="text-sm font-medium text-zinc-300 uppercase tracking-widest mb-4">
        Request Payout
      </h2>

      <div className="flex flex-col sm:flex-row gap-3">
        <input
          type="number"
          placeholder="Amount in ₹"
          value={amountRupees}
          onChange={(e) => setAmountRupees(e.target.value)}
          min="1"
          step="0.01"
          className="flex-1 bg-zinc-800/50 border border-zinc-700/40 text-zinc-200 text-sm rounded-lg px-4 py-2.5 focus:outline-none focus:border-zinc-500 transition-colors placeholder-zinc-600"
        />

        <select
          value={selectedBank}
          onChange={(e) => setSelectedBank(e.target.value)}
          className="bg-zinc-800/50 border border-zinc-700/40 text-zinc-200 text-sm rounded-lg px-4 py-2.5 focus:outline-none focus:border-zinc-500 transition-colors cursor-pointer"
        >
          {merchant.bank_accounts?.map((ba) => (
            <option key={ba.id} value={ba.id}>
              {ba.account_holder_name} — ****{ba.account_number.slice(-4)}
            </option>
          ))}
        </select>

        <button
          onClick={handleSubmit}
          disabled={submitting || !amountRupees}
          className="bg-emerald-500 hover:bg-emerald-400 disabled:bg-zinc-700 disabled:text-zinc-500 text-zinc-950 font-medium text-sm px-6 py-2.5 rounded-lg transition-colors cursor-pointer disabled:cursor-not-allowed"
        >
          {submitting ? "Submitting…" : "Request"}
        </button>
      </div>

      {message && (
        <p className={`mt-3 text-sm ${message.type === "success" ? "text-emerald-400" : "text-red-400"}`}>
          {message.text}
        </p>
      )}
    </div>
  );
}