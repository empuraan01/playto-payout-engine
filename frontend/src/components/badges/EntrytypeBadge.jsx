const colors = {
  credit: "text-emerald-400",
  debit_hold: "text-amber-400",
  debit_confirm: "text-red-400",
  debit_release: "text-blue-400",
};

const labels = {
  credit: "Credit",
  debit_hold: "Hold",
  debit_confirm: "Confirmed",
  debit_release: "Released",
};

export default function EntryTypeBadge({ type }) {
  return (
    <span className={`text-xs font-semibold tracking-wide uppercase ${colors[type] || ""}`}>
      {labels[type] || type}
    </span>
  );
}