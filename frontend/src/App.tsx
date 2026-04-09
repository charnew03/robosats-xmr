import { useEffect, useMemo, useState } from "react";
import { getOffers, type Offer } from "./api";

type SideFilter = "all" | "buy" | "sell";

function App() {
  const [offers, setOffers] = useState<Offer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sideFilter, setSideFilter] = useState<SideFilter>("all");
  const [paymentFilter, setPaymentFilter] = useState("");
  const [amountMinFilter, setAmountMinFilter] = useState("");
  const [amountMaxFilter, setAmountMaxFilter] = useState("");
  const [premiumMaxFilter, setPremiumMaxFilter] = useState("");

  useEffect(() => {
    document.documentElement.classList.add("dark");
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let mounted = true;

    async function fetchOffers() {
      setLoading(true);
      setError(null);
      try {
        const data = await getOffers(controller.signal);
        if (mounted) {
          setOffers(data);
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : "Unknown error");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    fetchOffers();
    const intervalId = window.setInterval(fetchOffers, 10000);

    return () => {
      mounted = false;
      controller.abort();
      window.clearInterval(intervalId);
    };
  }, []);

  const filteredOffers = useMemo(() => {
    return offers.filter((offer) => {
      // Current backend offers map to maker sell-intent; keep side filter ready for future buy-side offers.
      const side = "sell";
      if (sideFilter !== "all" && side !== sideFilter) {
        return false;
      }

      if (
        paymentFilter &&
        !offer.payment_method.toLowerCase().includes(paymentFilter.toLowerCase())
      ) {
        return false;
      }

      const minAmount = amountMinFilter ? Number(amountMinFilter) : null;
      const maxAmount = amountMaxFilter ? Number(amountMaxFilter) : null;
      const maxPremium = premiumMaxFilter ? Number(premiumMaxFilter) : null;

      if (minAmount !== null && !Number.isNaN(minAmount) && offer.amount_xmr < minAmount) {
        return false;
      }
      if (maxAmount !== null && !Number.isNaN(maxAmount) && offer.amount_xmr > maxAmount) {
        return false;
      }
      if (
        maxPremium !== null &&
        !Number.isNaN(maxPremium) &&
        offer.premium_pct > maxPremium
      ) {
        return false;
      }

      return true;
    });
  }, [offers, sideFilter, paymentFilter, amountMinFilter, amountMaxFilter, premiumMaxFilter]);

  return (
    <div className="min-h-screen bg-xmr-bg text-xmr-text">
      <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-xmr-muted">RoboSats XMR</p>
            <h1 className="text-3xl font-semibold">Order Book</h1>
            <p className="mt-2 text-sm text-xmr-muted">
              Active maker offers from `GET /offers` with live refresh every 10 seconds.
            </p>
          </div>
          <button
            onClick={() => window.location.reload()}
            className="rounded-md border border-xmr-border bg-xmr-panel px-4 py-2 text-sm font-medium hover:border-xmr-accent hover:text-xmr-accentSoft"
            type="button"
          >
            Refresh now
          </button>
        </header>

        <section className="mb-6 grid gap-3 rounded-lg border border-xmr-border bg-xmr-panel p-4 sm:grid-cols-2 lg:grid-cols-5">
          <label className="text-sm">
            <span className="mb-1 block text-xmr-muted">Side</span>
            <select
              className="w-full rounded-md border border-xmr-border bg-black/20 px-3 py-2"
              value={sideFilter}
              onChange={(e) => setSideFilter(e.target.value as SideFilter)}
            >
              <option value="all">All</option>
              <option value="buy">Buy XMR</option>
              <option value="sell">Sell XMR</option>
            </select>
          </label>

          <label className="text-sm">
            <span className="mb-1 block text-xmr-muted">Payment method</span>
            <input
              value={paymentFilter}
              onChange={(e) => setPaymentFilter(e.target.value)}
              placeholder="SEPA, Revolut..."
              className="w-full rounded-md border border-xmr-border bg-black/20 px-3 py-2"
            />
          </label>

          <label className="text-sm">
            <span className="mb-1 block text-xmr-muted">Min amount (XMR)</span>
            <input
              value={amountMinFilter}
              onChange={(e) => setAmountMinFilter(e.target.value)}
              type="number"
              min="0"
              step="0.0001"
              className="w-full rounded-md border border-xmr-border bg-black/20 px-3 py-2"
            />
          </label>

          <label className="text-sm">
            <span className="mb-1 block text-xmr-muted">Max amount (XMR)</span>
            <input
              value={amountMaxFilter}
              onChange={(e) => setAmountMaxFilter(e.target.value)}
              type="number"
              min="0"
              step="0.0001"
              className="w-full rounded-md border border-xmr-border bg-black/20 px-3 py-2"
            />
          </label>

          <label className="text-sm">
            <span className="mb-1 block text-xmr-muted">Max premium (%)</span>
            <input
              value={premiumMaxFilter}
              onChange={(e) => setPremiumMaxFilter(e.target.value)}
              type="number"
              step="0.1"
              className="w-full rounded-md border border-xmr-border bg-black/20 px-3 py-2"
            />
          </label>
        </section>

        {loading && (
          <div className="rounded-lg border border-xmr-border bg-xmr-panel p-5 text-sm text-xmr-muted">
            Loading offers...
          </div>
        )}

        {error && (
          <div className="rounded-lg border border-red-900 bg-red-950/30 p-5 text-sm text-red-200">
            Could not load offers: {error}
          </div>
        )}

        {!loading && !error && (
          <section className="overflow-hidden rounded-lg border border-xmr-border bg-xmr-panel">
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-black/20 text-xmr-muted">
                  <tr>
                    <th className="px-4 py-3 font-medium">Maker</th>
                    <th className="px-4 py-3 font-medium">Amount (XMR)</th>
                    <th className="px-4 py-3 font-medium">Premium</th>
                    <th className="px-4 py-3 font-medium">Fiat</th>
                    <th className="px-4 py-3 font-medium">Payment</th>
                    <th className="px-4 py-3 font-medium">Maker bond</th>
                    <th className="px-4 py-3 font-medium">Taker bond</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredOffers.length === 0 ? (
                    <tr>
                      <td className="px-4 py-6 text-xmr-muted" colSpan={7}>
                        No offers match the current filters.
                      </td>
                    </tr>
                  ) : (
                    filteredOffers.map((offer) => (
                      <tr key={offer.offer_id} className="border-t border-xmr-border">
                        <td className="px-4 py-3">{offer.maker_id}</td>
                        <td className="px-4 py-3">{offer.amount_xmr.toFixed(4)}</td>
                        <td className="px-4 py-3">{offer.premium_pct.toFixed(2)}%</td>
                        <td className="px-4 py-3">{offer.fiat_currency}</td>
                        <td className="px-4 py-3">{offer.payment_method}</td>
                        <td className="px-4 py-3">{offer.maker_bond_amount.toFixed(4)}</td>
                        <td className="px-4 py-3">{offer.taker_bond_amount.toFixed(4)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
