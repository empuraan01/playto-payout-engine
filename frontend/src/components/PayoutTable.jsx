import StatusBadge from "./badges/StatusBadge";
import { formatPaise, formatDate } from "../utils/format";

export default function PayoutTable({ payouts }) {
  return (
    <div className="bg-zinc-900/50 border border-zinc-800/40 rounded-xl overflow-hidden">
      <div className="px-6 py-4 border-b border-zinc-800/40">
        <h2 className="text-sm font-medium text-zinc-300 uppercase tracking-widest">Payouts</h2>
      </div>
      <div className="divide-y divide-zinc-800/30">
        {payouts.length === 0 ? (
          <p className="px-6 py-8 text-zinc-600 text-sm text-center">No payouts yet</p>
        ) : (
          payouts.map((payout) => (
            <div key={payout.id} className="px-6 py-3.5 flex items-center justify-between">
              <div className="flex flex-col gap-1.5">
                <StatusBadge status={payout.status} />
                <span className="text-xs text-zinc-600 font-mono">{payout.id.slice(0, 8)}…</span>
              </div>
              <div className="text-right">
                <p className="text-sm font-medium text-zinc-200 tabular-nums">
                  {formatPaise(payout.amount_paise)}
                </p>
                <p className="text-xs text-zinc-600 mt-0.5">{formatDate(payout.created_at)}</p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}