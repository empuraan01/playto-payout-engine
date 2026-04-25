import EntryTypeBadge from "./badges/EntrytypeBadge";
import { formatPaise, formatDate } from "../utils/format";

export default function LedgerTable({ ledger }) {
  return (
    <div className="bg-zinc-900/50 border border-zinc-800/40 rounded-xl overflow-hidden">
      <div className="px-6 py-4 border-b border-zinc-800/40">
        <h2 className="text-sm font-medium text-zinc-300 uppercase tracking-widest">Ledger</h2>
      </div>
      <div className="divide-y divide-zinc-800/30">
        {ledger.length === 0 ? (
          <p className="px-6 py-8 text-zinc-600 text-sm text-center">No entries yet</p>
        ) : (
          ledger.map((entry) => (
            <div key={entry.id} className="px-6 py-3.5 flex items-center justify-between">
              <div className="flex flex-col gap-1">
                <EntryTypeBadge type={entry.entry_type} />
                <span className="text-xs text-zinc-500">{entry.description || "—"}</span>
              </div>
              <div className="text-right">
                <p className={`text-sm font-medium tabular-nums ${
                  entry.entry_type === "credit" || entry.entry_type === "debit_release"
                    ? "text-emerald-400"
                    : "text-red-400"
                }`}>
                  {entry.entry_type === "credit" || entry.entry_type === "debit_release" ? "+" : "−"}
                  {formatPaise(entry.amount_paise)}
                </p>
                <p className="text-xs text-zinc-600 mt-0.5">{formatDate(entry.created_at)}</p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}