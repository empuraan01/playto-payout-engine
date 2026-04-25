export default function Header({ merchants, selectedMerchant, onSelectMerchant }) {
  return (
    <header className="border-b border-zinc-800/60 bg-zinc-950/80 backdrop-blur-sm sticky top-0 z-10">
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <h1 className="text-lg font-semibold tracking-tight text-zinc-100">
            Playto <span className="text-zinc-500 font-normal">Pay</span>
          </h1>
        </div>

        <select
          value={selectedMerchant?.id || ""}
          onChange={(e) => {
            const m = merchants.find((m) => m.id === e.target.value);
            onSelectMerchant(m);
          }}
          className="bg-zinc-900 border border-zinc-700/50 text-zinc-200 text-sm rounded-lg px-4 py-2 focus:outline-none focus:border-zinc-500 transition-colors cursor-pointer"
        >
          {merchants.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name}
            </option>
          ))}
        </select>
      </div>
    </header>
  );
}