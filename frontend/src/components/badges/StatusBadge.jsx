const colors = {
  pending: "bg-amber-400/15 text-amber-300 border border-amber-400/20",
  processing: "bg-blue-400/15 text-blue-300 border border-blue-400/20",
  completed: "bg-emerald-400/15 text-emerald-300 border border-emerald-400/20",
  failed: "bg-red-400/15 text-red-300 border border-red-400/20",
};

export default function StatusBadge({ status }) {
  return (
    <span className={`px-2.5 py-1 rounded-full text-xs font-medium tracking-wide uppercase ${colors[status] || ""}`}>
      {status}
    </span>
  );
}