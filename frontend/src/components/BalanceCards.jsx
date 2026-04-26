import { formatPaise } from "../utils/format";

export default function BalanceCards({ balance }) {
  if (!balance) return null;

  const cards = [
    { label: "Available Balance", value: balance.available_balance, color: "text-emerald-400" },
    { label: "Held Balance", value: balance.held_balance, color: "text-amber-400" },
    { label: "Total Balance", value: balance.available_balance + balance.held_balance, color: "text-zinc-100" },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {cards.map((card) => (
        <div key={card.label} className="bg-zinc-900/50 border border-zinc-800/40 rounded-xl p-6">
          <p className="text-xs text-zinc-500 uppercase tracking-widest mb-2">{card.label}</p>
          <p className={`text-2xl font-semibold tabular-nums ${card.color}`}>
            {formatPaise(card.value)}
          </p>
        </div>
      ))}
    </div>
  );
}