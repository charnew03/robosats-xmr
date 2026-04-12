import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getOffers, type Offer } from "../api";
import { OfferRowCard } from "../components/OfferRowCard";
import { Spinner } from "../components/Spinner";
import { TakeOfferModal } from "../components/TakeOfferModal";
import { useToast } from "../context/ToastContext";
import { formatFiatCurrency, formatPremium, formatXmr, shortId } from "../lib/format";
import { filterOffers, type SideFilter } from "../lib/offerFilters";

export function OrderBookPage() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [offers, setOffers] = useState<Offer[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sideFilter, setSideFilter] = useState<SideFilter>("all");
  const [paymentFilter, setPaymentFilter] = useState("");
  const [amountMinFilter, setAmountMinFilter] = useState("");
  const [amountMaxFilter, setAmountMaxFilter] = useState("");
  const [premiumMinFilter, setPremiumMinFilter] = useState("");
  const [premiumMaxFilter, setPremiumMaxFilter] = useState("");
  const [takeOfferTarget, setTakeOfferTarget] = useState<Offer | null>(null);

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
        .catch(() => {});
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
        premiumMin: premiumMinFilter,
      }),
    [
      offers,
      sideFilter,
      paymentFilter,
      amountMinFilter,
      amountMaxFilter,
      premiumMaxFilter,
      premiumMinFilter,
    ],
  );

  const clearFilters = useCallback(() => {
    setSideFilter("all");
    setPaymentFilter("");
    setAmountMinFilter("");
    setAmountMaxFilter("");
    setPremiumMinFilter("");
    setPremiumMaxFilter("");
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    setError(null);
    try {
      const data = await getOffers();
      setOffers(data);
      showToast("success", "Order book refreshed.");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setError(msg);
      showToast("error", msg);
    } finally {
      setRefreshing(false);
    }
  };

  const onTakeSuccess = useCallback(
    (tradeId: string, removedOfferId: string) => {
      showToast("success", `Trade created. Opening trade…`);
      setOffers((prev) => prev.filter((o) => o.offer_id !== removedOfferId));
      void getOffers()
        .then(setOffers)
        .catch(() => {});
      navigate(`/trade/${tradeId}`);
    },
    [navigate, showToast],
  );

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <header className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-xmr-muted">RoboSats XMR</p>
          <h1 className="text-3xl font-semibold">Order book</h1>
          <p className="mt-2 max-w-xl text-sm text-xmr-muted">
            Filters apply instantly. <strong className="text-xmr-text">Buy XMR</strong> matches current listings
            (makers sell XMR). <strong className="text-xmr-text">Sell XMR</strong> is reserved for a future API
            shape.
          </p>
          <p className="mt-3 max-w-xl rounded-md border border-xmr-border bg-xmr-panel px-3 py-2 text-sm text-xmr-accentSoft">
            <strong className="text-xmr-text">Take offer</strong> opens a short form (taker account id). Escrow + bonds
            are allocated on the server.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={clearFilters}
            className="rounded-md border border-xmr-border bg-transparent px-4 py-2 text-sm text-xmr-muted hover:border-xmr-muted hover:text-xmr-text"
          >
            Clear filters
          </button>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="inline-flex items-center gap-2 rounded-md border border-xmr-border bg-xmr-panel px-4 py-2 text-sm font-medium hover:border-xmr-accent hover:text-xmr-accentSoft disabled:opacity-50"
            type="button"
          >
            {refreshing ? <Spinner /> : null}
            {refreshing ? "Refreshing…" : "Refresh now"}
          </button>
        </div>
      </header>

      <section className="mb-4 grid gap-3 rounded-lg border border-xmr-border bg-xmr-panel p-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
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

        <label className="text-sm lg:col-span-2">
          <span className="mb-1 block text-xmr-muted">Payment method</span>
          <input
            value={paymentFilter}
            onChange={(e) => setPaymentFilter(e.target.value)}
            placeholder="Substring match, e.g. SEPA"
            className="w-full rounded-md border border-xmr-border bg-black/20 px-3 py-2"
          />
        </label>

        <label className="text-sm">
          <span className="mb-1 block text-xmr-muted">Min XMR</span>
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
          <span className="mb-1 block text-xmr-muted">Max XMR</span>
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
          <span className="mb-1 block text-xmr-muted">Min premium (%)</span>
          <input
            value={premiumMinFilter}
            onChange={(e) => setPremiumMinFilter(e.target.value)}
            type="number"
            step="0.1"
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

      {offers.length > 0 && filteredOffers.length === 0 && sideFilter !== "all" && (
        <div className="mb-4 rounded-lg border border-amber-900/60 bg-amber-950/25 px-4 py-3 text-sm text-amber-100">
          {sideFilter === "sell" ? (
            <>
              <strong>No “Sell XMR” rows.</strong> Switch to <strong>All</strong> or <strong>Buy XMR</strong>.
            </>
          ) : (
            <>No rows match filters — try <button type="button" className="underline" onClick={clearFilters}>clear filters</button>.</>
          )}
        </div>
      )}

      <p className="mb-4 text-sm text-xmr-muted">
        Showing <strong className="text-xmr-text">{filteredOffers.length}</strong> of {offers.length} offers
        {loading && " · loading…"}
      </p>

      {error && (
        <div className="mb-4 rounded-lg border border-red-900 bg-red-950/30 p-5 text-sm text-red-200">
          {error}
        </div>
      )}

      {loading && offers.length === 0 && !error && (
        <div className="flex items-center gap-2 rounded-lg border border-xmr-border bg-xmr-panel p-5 text-sm text-xmr-muted">
          <Spinner className="h-5 w-5" />
          Loading offers…
        </div>
      )}

      {(!loading || offers.length > 0) && !error && (
        <section className="overflow-hidden rounded-lg border border-xmr-border bg-xmr-panel">
          <div className="space-y-3 p-3 md:hidden">
            {filteredOffers.length === 0 ? (
              <p className="py-6 text-center text-sm text-xmr-muted">
                {sideFilter === "sell" ? (
                  <>
                    No listings. Use <strong className="text-xmr-text">Buy XMR</strong> or <strong>All</strong>.
                  </>
                ) : (
                  <>No offers match filters.</>
                )}
              </p>
            ) : (
              filteredOffers.map((offer) => (
                <OfferRowCard key={offer.offer_id} offer={offer} onTake={setTakeOfferTarget} />
              ))
            )}
          </div>

          <div className="hidden overflow-x-auto md:block">
            <table className="w-full min-w-[860px] table-fixed text-left text-sm">
              <colgroup>
                <col className="w-[120px]" />
                <col className="w-[100px]" />
                <col className="w-[100px]" />
                <col className="w-[88px]" />
                <col className="w-[64px]" />
                <col className="w-[minmax(120px,1fr)]" />
                <col className="w-[120px]" />
                <col className="w-[112px]" />
              </colgroup>
              <thead className="bg-black/20 text-xmr-muted">
                <tr>
                  <th className="px-3 py-3 font-medium">Side</th>
                  <th className="px-3 py-3 font-medium">Maker</th>
                  <th className="px-3 py-3 font-medium">XMR</th>
                  <th className="px-3 py-3 font-medium">Prem.</th>
                  <th className="px-3 py-3 font-medium">Fiat</th>
                  <th className="px-3 py-3 font-medium">Payment</th>
                  <th className="px-3 py-3 font-medium">Bonds</th>
                  <th className="sticky right-0 z-10 border-l border-xmr-border bg-xmr-panel px-3 py-3 text-right font-medium shadow-[-8px_0_12px_-8px_rgba(0,0,0,0.5)]">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredOffers.length === 0 ? (
                  <tr>
                    <td className="px-3 py-8 text-xmr-muted" colSpan={8}>
                      No offers match filters.
                    </td>
                  </tr>
                ) : (
                  filteredOffers.map((offer) => (
                    <tr key={offer.offer_id} className="border-t border-xmr-border hover:bg-white/[0.03]">
                      <td className="px-3 py-3 align-top">
                        <span className="inline-block rounded bg-emerald-950/60 px-2 py-0.5 text-xs text-emerald-200">
                          Sell
                        </span>
                      </td>
                      <td className="truncate px-3 py-3 font-mono text-xs" title={offer.maker_id}>
                        {shortId(offer.maker_id)}
                      </td>
                      <td className="px-3 py-3 font-mono">{formatXmr(offer.amount_xmr)}</td>
                      <td className="px-3 py-3">{formatPremium(offer.premium_pct)}</td>
                      <td className="px-3 py-3 font-medium">{formatFiatCurrency(offer.fiat_currency)}</td>
                      <td className="break-words px-3 py-3">{offer.payment_method}</td>
                      <td className="px-3 py-3 font-mono text-xs text-xmr-muted">
                        {formatXmr(offer.maker_bond_amount)} / {formatXmr(offer.taker_bond_amount)}
                      </td>
                      <td className="sticky right-0 z-10 border-l border-xmr-border bg-xmr-panel px-3 py-3 text-right shadow-[-8px_0_12px_-8px_rgba(0,0,0,0.5)]">
                        <button
                          type="button"
                          onClick={() => setTakeOfferTarget(offer)}
                          className="rounded-md bg-xmr-accent px-3 py-1.5 text-xs font-semibold text-black hover:bg-xmr-accentSoft"
                        >
                          Take
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

      {takeOfferTarget && (
        <TakeOfferModal
          offer={takeOfferTarget}
          onClose={() => setTakeOfferTarget(null)}
          onSuccess={(tradeId) => onTakeSuccess(tradeId, takeOfferTarget.offer_id)}
          onError={(msg) => showToast("error", msg)}
        />
      )}
    </main>
  );
}
