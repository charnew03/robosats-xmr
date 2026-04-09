import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getOffers, type Offer } from "./api";
import { TakeOfferModal } from "./components/TakeOfferModal";
import { Toast, type ToastState } from "./components/Toast";
import { formatFiatCurrency, formatPremium, formatXmr, shortId } from "./lib/format";
import { filterOffers, type SideFilter } from "./lib/offerFilters";

function App() {
  const [offers, setOffers] = useState<Offer[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sideFilter, setSideFilter] = useState<SideFilter>("all");
  const [paymentFilter, setPaymentFilter] = useState("");
  const [amountMinFilter, setAmountMinFilter] = useState("");
  const [amountMaxFilter, setAmountMaxFilter] = useState("");
  const [premiumMaxFilter, setPremiumMaxFilter] = useState("");
  const [takeOfferTarget, setTakeOfferTarget] = useState<Offer | null>(null);
  const [toast, setToast] = useState<ToastState>(null);
  const toastIdRef = useRef(0);

  const showToast = useCallback((kind: "success" | "error" | "info", message: string) => {
    toastIdRef.current += 1;
    setToast({ id: toastIdRef.current, kind, message });
  }, []);

  const dismissToast = useCallback(() => setToast(null), []);

  useEffect(() => {
    document.documentElement.classList.add("dark");
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let mounted = true;

    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getOffers(controller.signal);
        if (mounted) setOffers(data);
      } catch (err) {
        if (mounted && !(err instanceof Error && err.name === "AbortError")) {
          setError(err instanceof Error ? err.message : "Unknown error");
        }
      } finally {
        if (mounted) setLoading(false);
      }
    })();

    const intervalId = window.setInterval(() => {
      const c = new AbortController();
      getOffers(c.signal)
        .then((data) => {
          if (mounted) setOffers(data);
        })
        .catch(() => {
          /* silent poll failure */
        });
    }, 10000);

    return () => {
      mounted = false;
      controller.abort();
      window.clearInterval(intervalId);
    };
  }, []);

  const filteredOffers = useMemo(
    () =>
      filterOffers(offers, {
        side: sideFilter,
        payment: paymentFilter,
        amountMin: amountMinFilter,
        amountMax: amountMaxFilter,
        premiumMax: premiumMaxFilter,
      }),
    [offers, sideFilter, paymentFilter, amountMinFilter, amountMaxFilter, premiumMaxFilter],
  );

  const handleRefresh = async () => {
    setRefreshing(true);
    setError(null);
    try {
      const data = await getOffers();
      setOffers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="min-h-screen bg-xmr-bg text-xmr-text">
      <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-xmr-muted">RoboSats XMR</p>
            <h1 className="text-3xl font-semibold">Order book</h1>
            <p className="mt-2 max-w-xl text-sm text-xmr-muted">
              Live offers from <code className="rounded bg-black/30 px-1">GET /offers</code>.{" "}
              <strong className="text-xmr-text">Buy XMR</strong> lists makers selling XMR for fiat.{" "}
              <strong className="text-xmr-text">Sell XMR</strong> (you sell) has no listings until the API adds
              buy-side offers.
            </p>
          </div>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="rounded-md border border-xmr-border bg-xmr-panel px-4 py-2 text-sm font-medium hover:border-xmr-accent hover:text-xmr-accentSoft disabled:opacity-50"
            type="button"
          >
            {refreshing ? "Refreshing…" : "Refresh now"}
          </button>
        </header>

        <section className="mb-4 grid gap-3 rounded-lg border border-xmr-border bg-xmr-panel p-4 sm:grid-cols-2 lg:grid-cols-5">
          <label className="text-sm">
            <span className="mb-1 block text-xmr-muted">Side</span>
            <select
              className="w-full rounded-md border border-xmr-border bg-black/20 px-3 py-2"
              value={sideFilter}
              onChange={(e) => setSideFilter(e.target.value as SideFilter)}
            >
              <option value="all">All</option>
              <option value="buy">Buy XMR (take sell offers)</option>
              <option value="sell">Sell XMR (your XMR → fiat)</option>
            </select>
          </label>

          <label className="text-sm">
            <span className="mb-1 block text-xmr-muted">Payment method</span>
            <input
              value={paymentFilter}
              onChange={(e) => setPaymentFilter(e.target.value)}
              placeholder="SEPA, Revolut…"
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

        <p className="mb-4 text-sm text-xmr-muted">
          Showing <strong className="text-xmr-text">{filteredOffers.length}</strong> of {offers.length} loaded offers
          {loading && " · loading…"}
        </p>

        {error && (
          <div className="mb-4 rounded-lg border border-red-900 bg-red-950/30 p-5 text-sm text-red-200">
            Could not load offers: {error}
          </div>
        )}

        {loading && offers.length === 0 && !error && (
          <div className="rounded-lg border border-xmr-border bg-xmr-panel p-5 text-sm text-xmr-muted">
            Loading offers…
          </div>
        )}

        {(!loading || offers.length > 0) && !error && (
          <section className="overflow-hidden rounded-lg border border-xmr-border bg-xmr-panel">
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-black/20 text-xmr-muted">
                  <tr>
                    <th className="px-4 py-3 font-medium">Side</th>
                    <th className="px-4 py-3 font-medium">Maker</th>
                    <th className="px-4 py-3 font-medium">XMR</th>
                    <th className="px-4 py-3 font-medium">Premium</th>
                    <th className="px-4 py-3 font-medium">Fiat</th>
                    <th className="px-4 py-3 font-medium">Payment</th>
                    <th className="hidden md:table-cell px-4 py-3 font-medium">Bonds (M/T)</th>
                    <th className="px-4 py-3 font-medium text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredOffers.length === 0 ? (
                    <tr>
                      <td className="px-4 py-8 text-xmr-muted" colSpan={8}>
                        {sideFilter === "sell" ? (
                          <>
                            No <strong>sell-XMR</strong> listings match filters. Current API only exposes{" "}
                            <strong>makers selling XMR</strong> (use <strong>Buy XMR</strong> or <strong>All</strong>).
                          </>
                        ) : (
                          <>No offers match the current filters.</>
                        )}
                      </td>
                    </tr>
                  ) : (
                    filteredOffers.map((offer) => (
                      <tr key={offer.offer_id} className="border-t border-xmr-border hover:bg-white/[0.03]">
                        <td className="px-4 py-3">
                          <span className="rounded bg-emerald-950/60 px-2 py-0.5 text-xs text-emerald-200">
                            Sell XMR
                          </span>
                          <span className="ml-2 text-xs text-xmr-muted">→ you buy</span>
                        </td>
                        <td className="px-4 py-3 font-mono text-xs" title={offer.maker_id}>
                          {shortId(offer.maker_id)}
                        </td>
                        <td className="px-4 py-3 font-mono">{formatXmr(offer.amount_xmr)}</td>
                        <td className="px-4 py-3">{formatPremium(offer.premium_pct)}</td>
                        <td className="px-4 py-3 font-medium">{formatFiatCurrency(offer.fiat_currency)}</td>
                        <td className="px-4 py-3">{offer.payment_method}</td>
                        <td className="hidden md:table-cell px-4 py-3 font-mono text-xs text-xmr-muted">
                          {formatXmr(offer.maker_bond_amount)} / {formatXmr(offer.taker_bond_amount)}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            type="button"
                            onClick={() => setTakeOfferTarget(offer)}
                            className="rounded-md bg-xmr-accent px-3 py-1.5 text-xs font-semibold text-black hover:bg-xmr-accentSoft"
                          >
                            Take offer
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </main>

      {takeOfferTarget && (
        <TakeOfferModal
          offer={takeOfferTarget}
          onClose={() => setTakeOfferTarget(null)}
          onSuccess={(tradeId) => {
            const removedId = takeOfferTarget.offer_id;
            showToast(
              "success",
              `Trade created: ${tradeId}. Fund escrow + bonds per coordinator instructions.`,
            );
            setOffers((prev) => prev.filter((o) => o.offer_id !== removedId));
            void getOffers()
              .then(setOffers)
              .catch(() => {});
          }}
          onError={(msg) => showToast("error", msg)}
        />
      )}

      <Toast toast={toast} onDismiss={dismissToast} />
    </div>
  );
}

export default App;
