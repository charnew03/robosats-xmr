import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getOffers, getTrades, type Offer, type Trade } from "../api";
import { Avatar } from "../components/Avatar";
import { Spinner } from "../components/Spinner";
import { useProfile } from "../context/ProfileContext";
import { useToast } from "../context/ToastContext";
import { formatPremium, formatXmr, shortId } from "../lib/format";
import { loadOfferNote } from "../lib/offerNoteStorage";

export function DashboardPage() {
  const { pseudonym } = useProfile();
  const { showToast } = useToast();
  const [offers, setOffers] = useState<Offer[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [o, t] = await Promise.all([getOffers(), getTrades()]);
      setOffers(o);
      setTrades(t);
    } catch (e) {
      showToast("error", e instanceof Error ? e.message : "Load failed");
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    void load();
  }, [load]);

  const pid = pseudonym.trim();
  const myOffers = useMemo(
    () => (pid ? offers.filter((o) => o.maker_id === pid) : []),
    [offers, pid],
  );
  const myTrades = useMemo(
    () =>
      pid
        ? trades.filter((t) => t.seller_id === pid || t.buyer_id === pid)
        : [],
    [trades, pid],
  );

  const terminalStates = useMemo(() => new Set(["RELEASED", "CANCELLED", "REFUNDED"]), []);
  const activeTrades = useMemo(
    () => myTrades.filter((t) => !terminalStates.has(t.state)),
    [myTrades, terminalStates],
  );
  const terminalTrades = useMemo(
    () => myTrades.filter((t) => terminalStates.has(t.state)),
    [myTrades, terminalStates],
  );

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="mt-1 text-sm text-xmr-muted">
            Filtered by your account id. Sign in from the header if this list is empty.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-md border border-xmr-border px-4 py-2 text-sm hover:border-xmr-accent disabled:opacity-50"
        >
          {loading ? <Spinner /> : null}
          Reload
        </button>
      </div>

      {!pid && (
        <p className="mb-6 rounded-lg border border-amber-900/50 bg-amber-950/20 p-4 text-sm text-amber-100">
          <strong>Log in</strong> with your seed phrase in the header to see your offers and trades.
        </p>
      )}

      {loading && !offers.length && !trades.length ? (
        <div className="flex items-center gap-2 text-xmr-muted">
          <Spinner className="h-5 w-5" /> Loading…
        </div>
      ) : null}

      <section className="mb-10">
        <h2 className="mb-3 text-lg font-medium">My active offers</h2>
        <p className="mb-3 text-xs text-xmr-muted">
          Only <strong>active</strong> offers are returned by the API. Taken offers move to trades.
        </p>
        {myOffers.length === 0 ? (
          <p className="text-sm text-xmr-muted">No active offers for this account.</p>
        ) : (
          <ul className="space-y-2">
            {myOffers.map((o) => (
              <li
                key={o.offer_id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-xmr-border bg-xmr-panel px-4 py-3"
              >
                <div className="flex items-center gap-3">
                  <Avatar pseudonym={o.maker_id} size="sm" />
                  <div>
                    <p className="font-mono text-sm">
                      {formatXmr(o.amount_xmr)} XMR · {formatPremium(o.premium_pct)} · {o.fiat_currency}
                    </p>
                    <p className="text-xs text-xmr-muted">{o.payment_method}</p>
                    {loadOfferNote(o.offer_id) ? (
                      <p className="mt-1 text-xs text-xmr-muted italic">
                        Note: {loadOfferNote(o.offer_id).slice(0, 120)}
                        {loadOfferNote(o.offer_id).length > 120 ? "…" : ""}
                      </p>
                    ) : null}
                  </div>
                </div>
                <span className="font-mono text-xs text-xmr-muted">{shortId(o.offer_id)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-lg font-medium">Active trades</h2>
        {activeTrades.length === 0 ? (
          <p className="text-sm text-xmr-muted">No active trades for this account.</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-xmr-border">
            <table className="w-full min-w-[600px] text-left text-sm">
              <thead className="bg-black/20 text-xmr-muted">
                <tr>
                  <th className="px-4 py-3">Role</th>
                  <th className="px-4 py-3">State</th>
                  <th className="px-4 py-3">XMR</th>
                  <th className="px-4 py-3">Counterparty</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {activeTrades.map((t) => {
                  const isSeller = t.seller_id === pid;
                  const counter = isSeller ? t.buyer_id ?? "—" : t.seller_id;
                  return (
                    <tr key={t.trade_id} className="border-t border-xmr-border">
                      <td className="px-4 py-3">{isSeller ? "Seller (maker)" : "Buyer (taker)"}</td>
                      <td className="px-4 py-3 font-medium">{t.state}</td>
                      <td className="px-4 py-3 font-mono">{formatXmr(t.amount_xmr)}</td>
                      <td className="px-4 py-3 font-mono text-xs">{shortId(counter)}</td>
                      <td className="px-4 py-3 text-right">
                        <Link
                          to={`/trade/${t.trade_id}`}
                          className="rounded-md bg-xmr-accent px-3 py-1.5 text-xs font-semibold text-black no-underline hover:bg-xmr-accentSoft"
                        >
                          Open
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {terminalTrades.length > 0 && (
          <details className="mt-4 text-sm">
            <summary className="cursor-pointer text-xmr-muted">Completed / terminal trades</summary>
            <ul className="mt-2 space-y-1 font-mono text-xs text-xmr-muted">
              {terminalTrades.map((t) => (
                  <li key={t.trade_id}>
                    <Link className="text-xmr-accentSoft hover:underline" to={`/trade/${t.trade_id}`}>
                      {shortId(t.trade_id)}
                    </Link>{" "}
                    — {t.state}
                  </li>
                ))}
            </ul>
          </details>
        )}
      </section>
    </main>
  );
}
