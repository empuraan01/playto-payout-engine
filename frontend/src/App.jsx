import { useState, useEffect } from "react";
import { fetchMerchants, fetchBalance, fetchLedger, fetchPayouts } from "./api/client";
import Header from "./components/Header";
import BalanceCards from "./components/BalanceCards";
import LedgerTable from "./components/LedgerTable";
import PayoutTable from "./components/PayoutTable";
import PayoutForm from "./components/PayoutForm";

export default function App() {
  const [merchants, setMerchants] = useState([]);
  const [selectedMerchant, setSelectedMerchant] = useState(null);
  const [balance, setBalance] = useState(null);
  const [ledger, setLedger] = useState([]);
  const [payouts, setPayouts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMerchants().then((res) => {
      setMerchants(res.data);
      if (res.data.length > 0) setSelectedMerchant(res.data[0]);
      setLoading(false);
    });
  }, []);

  const refreshData = (id) => {
    Promise.all([
      fetchBalance(id),
      fetchLedger(id),
      fetchPayouts(id),
    ]).then(([balRes, ledRes, payRes]) => {
      setBalance(balRes.data);
      setLedger(ledRes.data);
      setPayouts(payRes.data);
    });
  };

  useEffect(() => {
    if (!selectedMerchant) return;
    refreshData(selectedMerchant.id);
  }, [selectedMerchant]);

  // poll every 5 seconds
  useEffect(() => {
    if (!selectedMerchant) return;
    const interval = setInterval(() => refreshData(selectedMerchant.id), 5000);
    return () => clearInterval(interval);
  }, [selectedMerchant]);

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="text-zinc-500 tracking-widest uppercase text-sm">Loading…</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <Header
        merchants={merchants}
        selectedMerchant={selectedMerchant}
        onSelectMerchant={setSelectedMerchant}
      />
      <main className="max-w-6xl mx-auto px-6 py-8 space-y-8">
        <BalanceCards balance={balance} />
        <PayoutForm merchant={selectedMerchant} onSuccess={() => refreshData(selectedMerchant.id)} />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <LedgerTable ledger={ledger} />
          <PayoutTable payouts={payouts} />
        </div>
      </main>
    </div>
  );
}