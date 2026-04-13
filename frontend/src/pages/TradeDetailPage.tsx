import { type FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  cancelTrade,
  getTrade,
  markFiatPaid,
  openDispute,
  prepareMultisigRelease,
  refreshFunding,
  releaseEscrow,
  signMultisigRelease,
  submitMultisigRelease,
  type Trade,
} from "../api";
import { Avatar } from "../components/Avatar";
import { Spinner } from "../components/Spinner";
import { useProfile } from "../context/ProfileContext";
import { useToast } from "../context/ToastContext";
import { formatXmr, shortId } from "../lib/format";
import {
  appendChatMessage,
  loadChatMessages,
  type ChatMessage,
} from "../lib/chatStorage";

export function TradeDetailPage() {
  const { tradeId = "" } = useParams<{ tradeId: string }>();
  const { pseudonym } = useProfile();
  const { showToast } = useToast();
  const [trade, setTrade] = useState<Trade | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [showRelease, setShowRelease] = useState(false);
  const [showDispute, setShowDispute] = useState(false);
  const [showCancel, setShowCancel] = useState(false);
  const [payoutAddr, setPayoutAddr] = useState("");
  const [buyerSignHex, setBuyerSignHex] = useState("");
  const [sellerSignHex, setSellerSignHex] = useState("");
  const [makerReturn, setMakerReturn] = useState("");
  const [takerReturn, setTakerReturn] = useState("");
  const [disputeReason, setDisputeReason] = useState("");
  const [cancelReason, setCancelReason] = useState("");

  const load = useCallback(async () => {
    if (!tradeId) return;
    setLoading(true);
    try {
      const t = await getTrade(tradeId);
      setTrade(t);
    } catch (e) {
      showToast("error", e instanceof Error ? e.message : "Failed to load trade");
      setTrade(null);
    } finally {
      setLoading(false);
    }
  }, [tradeId, showToast]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!tradeId) return;
    setMessages(loadChatMessages(tradeId));
  }, [tradeId]);

  useEffect(() => {
    if (!tradeId) return;
    const id = window.setInterval(() => {
      getTrade(tradeId)
        .then(setTrade)
        .catch(() => {});
    }, 8000);
    return () => window.clearInterval(id);
  }, [tradeId]);

  const sendChat = (e: FormEvent) => {
    e.preventDefault();
    const who = pseudonym.trim();
    const text = chatInput.trim();
    if (!who || !text || !tradeId) return;
    const msg: ChatMessage = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      pseudonym: who,
      text,
      at: new Date().toISOString(),
    };
    setMessages(appendChatMessage(tradeId, msg));
    setChatInput("");
  };

  const run = async (fn: () => Promise<Trade>, successMessage = "Updated."): Promise<boolean> => {
    setBusy(true);
    try {
      const t = await fn();
      setTrade(t);
      showToast("success", successMessage);
      return true;
    } catch (e) {
      showToast("error", e instanceof Error ? e.message : "Action failed");
      return false;
    } finally {
      setBusy(false);
    }
  };

  const copyText = async (label: string, text: string) => {
    const v = text.trim();
    if (!v) {
      showToast("error", "Nothing to copy.");
      return;
    }
    try {
      await navigator.clipboard.writeText(v);
      showToast("success", `${label} copied.`);
    } catch {
      showToast("error", "Copy failed. Check browser permissions.");
    }
  };

  if (!tradeId) {
    return (
      <main className="px-4 py-8">
        <p>Missing trade id.</p>
      </main>
    );
  }

  if (loading && !trade) {
    return (
      <main className="flex items-center gap-2 px-4 py-12 text-xmr-muted">
        <Spinner className="h-6 w-6" /> Loading trade…
      </main>
    );
  }

  if (!trade) {
    return (
      <main className="px-4 py-8">
        <p>Trade not found.</p>
        <Link to="/dashboard" className="text-xmr-accentSoft hover:underline">
          Back to dashboard
        </Link>
      </main>
    );
  }

  const canCancel = trade.state === "CREATED" || trade.state === "FUNDS_PENDING";
  const canMarkFiat = trade.state === "FUNDED";
  const canRelease = trade.state === "FIAT_MARKED_PAID";
  const canDispute = trade.state === "FUNDED" || trade.state === "FIAT_MARKED_PAID";
  const canRefreshFunding = !["RELEASED", "CANCELLED", "REFUNDED"].includes(trade.state);
  const isMultisig = trade.escrow_mode === "MULTISIG_2OF3";

  return (
    <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <Link to="/dashboard" className="text-sm text-xmr-accentSoft hover:underline">
          ← Dashboard
        </Link>
        <button
          type="button"
          disabled={busy || !canRefreshFunding}
          onClick={() => void run(() => refreshFunding(tradeId), "Funding refreshed.")}
          className="rounded-md border border-xmr-border px-3 py-1.5 text-sm hover:border-xmr-accent disabled:opacity-40"
        >
          Refresh funding
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <h1 className="font-mono text-xl font-semibold">Trade {shortId(trade.trade_id)}</h1>
        <button
          type="button"
          disabled={busy}
          onClick={() => void copyText("Trade ID", trade.trade_id)}
          className="rounded-md border border-xmr-border px-2 py-1 text-xs text-xmr-muted hover:border-xmr-accent hover:text-xmr-accentSoft disabled:opacity-40"
        >
          Copy trade ID
        </button>
      </div>
      <p className="mt-1 text-sm text-xmr-muted">
        State: <strong className="text-xmr-text">{trade.state}</strong> · Confirmations{" "}
        {trade.current_confirmations}/{trade.required_confirmations}
      </p>

      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <section className="rounded-lg border border-xmr-border bg-xmr-panel p-4">
          <h2 className="text-sm font-medium text-xmr-muted">Parties</h2>
          <div className="mt-3 flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <Avatar pseudonym={trade.seller_id} />
              <div>
                <p className="text-xs text-xmr-muted">Seller (maker)</p>
                <p className="font-mono text-sm">{trade.seller_id}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Avatar pseudonym={trade.buyer_id ?? "?"} />
              <div>
                <p className="text-xs text-xmr-muted">Buyer (taker)</p>
                <p className="font-mono text-sm">{trade.buyer_id ?? "—"}</p>
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-lg border border-xmr-border bg-xmr-panel p-4">
          <h2 className="text-sm font-medium text-xmr-muted">Amounts & bonds</h2>
          <ul className="mt-3 space-y-2 font-mono text-sm">
            <li>Escrow (trade size): {formatXmr(trade.amount_xmr)} XMR</li>
            <li>Maker bond: {formatXmr(trade.maker_bond_amount)} XMR ({trade.maker_bond_confirmations} conf.)</li>
            <li>Taker bond: {formatXmr(trade.taker_bond_amount)} XMR ({trade.taker_bond_confirmations} conf.)</li>
            <li className="break-all text-xs text-xmr-muted">
              <span className="inline-flex flex-wrap items-center gap-2">
                <span>Deposit: {trade.deposit_address ?? "—"}</span>
                {trade.deposit_address ? (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void copyText("Deposit address", trade.deposit_address ?? "")}
                    className="shrink-0 rounded border border-xmr-border px-2 py-0.5 text-[11px] hover:border-xmr-accent disabled:opacity-40"
                  >
                    Copy deposit
                  </button>
                ) : null}
              </span>
            </li>
            <li className="text-xs text-xmr-muted">
              Escrow mode:{" "}
              <span className="font-medium text-xmr-text">
                {trade.escrow_mode === "MULTISIG_2OF3"
                  ? "2-of-3 multisig (buyer + seller + coordinator; release via prepare / sign / submit)"
                  : (trade.escrow_mode ?? "LEGACY_SUBADDRESS")}
              </span>
            </li>
            {isMultisig && trade.multisig_release_status && trade.multisig_release_status !== "idle" ? (
              <li className="text-xs text-xmr-muted">
                Multisig release:{" "}
                <span className="font-mono text-xmr-text">{trade.multisig_release_status}</span>
              </li>
            ) : null}
          </ul>
        </section>
      </div>

      <p className="mt-4 text-xs text-xmr-muted">
        Payment rails and exact fiat terms are coordinated out-of-band; the API stores the on-chain escrow and bond
        addresses. Share standard Monero receive addresses for payout and bond returns in{" "}
        <strong className="text-xmr-text">trade chat</strong> — the app never asks for a wallet connection or seed.{" "}
        <strong className="text-xmr-text">Payment method</strong> is not stored on the trade row in v1.
      </p>

      {trade.buyer_payout_address && (
        <p className="mt-2 text-xs text-xmr-muted">
          Buyer payout: <span className="font-mono">{trade.buyer_payout_address}</span>
        </p>
      )}
      {trade.release_txid && (
        <p className="mt-1 text-xs text-xmr-muted">
          Release txid: <span className="font-mono">{trade.release_txid}</span>
        </p>
      )}
      {trade.dispute_reason && (
        <p className="mt-2 rounded-md border border-red-900/40 bg-red-950/20 p-3 text-sm text-red-100">
          Dispute: {trade.dispute_reason}
        </p>
      )}

      <section className="mt-8 rounded-lg border border-xmr-border bg-xmr-panel p-4">
        <h2 className="text-sm font-medium">Actions</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={busy || !canMarkFiat}
            onClick={() =>
              void run(() => markFiatPaid(tradeId), "Fiat marked paid. Escrow can move to multisig release when ready.")
            }
            className="rounded-md bg-emerald-900/50 px-3 py-2 text-sm text-emerald-100 hover:bg-emerald-900 disabled:opacity-40"
          >
            Mark fiat paid
          </button>
          <button
            type="button"
            disabled={busy || !canRelease}
            onClick={() => {
              setBuyerSignHex("");
              setSellerSignHex("");
              setShowRelease(true);
            }}
            className="rounded-md bg-xmr-accent px-3 py-2 text-sm font-medium text-black hover:bg-xmr-accentSoft disabled:opacity-40"
          >
            {isMultisig ? "Release Escrow (2-of-3 Multisig)" : "Release XMR"}
          </button>
          <button
            type="button"
            disabled={busy || !canDispute}
            onClick={() => setShowDispute(true)}
            className="rounded-md border border-red-800/60 px-3 py-2 text-sm text-red-200 hover:bg-red-950/40 disabled:opacity-40"
          >
            Open dispute
          </button>
          <button
            type="button"
            disabled={busy || !canCancel}
            onClick={() => setShowCancel(true)}
            className="rounded-md border border-xmr-border px-3 py-2 text-sm hover:bg-white/5 disabled:opacity-40"
          >
            Collaborative cancel
          </button>
        </div>
        <p className="mt-2 text-xs text-xmr-muted">
          Buttons follow backend rules (e.g. release only after fiat marked). Wrong order returns an error toast.
        </p>
      </section>

      <section className="mt-8 rounded-lg border border-xmr-border bg-xmr-panel p-4">
        <h2 className="text-sm font-medium">Trade chat (MVP)</h2>
        <p className="mt-1 text-xs text-xmr-muted">
          Messages stay in <strong>this browser only</strong>. Use chat to exchange Monero addresses for payout and
          bond returns. Full end-to-end encrypted chat will replace this later.
        </p>
        <div className="mt-4 max-h-64 space-y-3 overflow-y-auto rounded-md border border-xmr-border bg-black/20 p-3">
          {messages.length === 0 ? (
            <p className="text-sm text-xmr-muted">No messages yet.</p>
          ) : (
            messages.map((m) => (
              <div key={m.id} className="flex gap-2 text-sm">
                <Avatar pseudonym={m.pseudonym} size="sm" />
                <div>
                  <p className="text-xs text-xmr-muted">
                    <span className="font-mono text-xmr-text">{m.pseudonym}</span> ·{" "}
                    {new Date(m.at).toLocaleString()}
                  </p>
                  <p className="mt-0.5 whitespace-pre-wrap">{m.text}</p>
                </div>
              </div>
            ))
          )}
        </div>
        <form onSubmit={sendChat} className="mt-3 flex gap-2">
          <input
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            placeholder={
              pseudonym.trim()
                ? "Message… (share XMR addresses here — no wallet connect in the app)"
                : "Sign in (nav) to chat using your account id as display name"
            }
            disabled={!pseudonym.trim()}
            className="min-w-0 flex-1 rounded-md border border-xmr-border bg-black/30 px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={!pseudonym.trim() || !chatInput.trim()}
            className="rounded-md border border-xmr-border px-4 py-2 text-sm hover:bg-white/5 disabled:opacity-40"
          >
            Send
          </button>
        </form>
      </section>

      {showRelease && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-4"
          onClick={() => setShowRelease(false)}
          role="presentation"
        >
          <div
            className="w-full max-w-md rounded-lg border border-xmr-border bg-xmr-panel p-4"
            onClick={(e) => e.stopPropagation()}
            role="presentation"
          >
            <h3 className="font-medium">
              {isMultisig ? "Release Escrow (2-of-3 Multisig)" : "Release escrow"}
            </h3>
            {isMultisig ? (
              <p className="mt-2 text-xs text-xmr-muted">
                Coordinator prepares the unsigned tx. Buyer and seller each run{" "}
                <span className="font-mono text-xmr-text">sign_multisig</span> in their own wallet and paste the updated
                hex (real stagenet). Fake-wallet dev mode can auto-simulate signatures when the hex fields are left
                empty.
              </p>
            ) : null}
            <label className="mt-3 block text-sm">
              <span className="text-xmr-muted">Buyer Monero payout address</span>
              <input
                value={payoutAddr}
                onChange={(e) => setPayoutAddr(e.target.value)}
                className="mt-1 w-full rounded-md border border-xmr-border bg-black/30 px-3 py-2 font-mono text-sm"
              />
            </label>
            <label className="mt-2 block text-sm">
              <span className="text-xmr-muted">Maker bond return (optional)</span>
              <input
                value={makerReturn}
                onChange={(e) => setMakerReturn(e.target.value)}
                className="mt-1 w-full rounded-md border border-xmr-border bg-black/30 px-3 py-2 font-mono text-sm"
              />
            </label>
            <label className="mt-2 block text-sm">
              <span className="text-xmr-muted">Taker bond return (optional)</span>
              <input
                value={takerReturn}
                onChange={(e) => setTakerReturn(e.target.value)}
                className="mt-1 w-full rounded-md border border-xmr-border bg-black/30 px-3 py-2 font-mono text-sm"
              />
            </label>
            {isMultisig && trade.multisig_pending_tx_data_hex ? (
              <div className="mt-3 rounded-md border border-xmr-border bg-black/25 p-2">
                <p className="text-xs text-xmr-muted">Pending multisig tx (share with signers)</p>
                <p className="mt-1 max-h-24 overflow-y-auto break-all font-mono text-[11px] text-xmr-text">
                  {trade.multisig_pending_tx_data_hex}
                </p>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void copyText("Multisig tx hex", trade.multisig_pending_tx_data_hex ?? "")}
                  className="mt-2 rounded border border-xmr-border px-2 py-1 text-xs hover:border-xmr-accent disabled:opacity-40"
                >
                  Copy pending tx hex
                </button>
              </div>
            ) : null}
            {isMultisig ? (
              <>
                <label className="mt-3 block text-sm">
                  <span className="text-xmr-muted">Buyer sign_multisig output (optional if fake auto path)</span>
                  <textarea
                    value={buyerSignHex}
                    onChange={(e) => setBuyerSignHex(e.target.value)}
                    rows={2}
                    className="mt-1 w-full rounded-md border border-xmr-border bg-black/30 px-3 py-2 font-mono text-[11px]"
                  />
                </label>
                <label className="mt-2 block text-sm">
                  <span className="text-xmr-muted">Seller sign_multisig output (optional if fake auto path)</span>
                  <textarea
                    value={sellerSignHex}
                    onChange={(e) => setSellerSignHex(e.target.value)}
                    rows={2}
                    className="mt-1 w-full rounded-md border border-xmr-border bg-black/30 px-3 py-2 font-mono text-[11px]"
                  />
                </label>
              </>
            ) : null}
            <div className="mt-4 flex flex-wrap justify-end gap-2">
              <button
                type="button"
                className="rounded-md border px-3 py-2 text-sm"
                onClick={() => setShowRelease(false)}
              >
                Close
              </button>
              {isMultisig ? (
                <>
                  <button
                    type="button"
                    disabled={busy}
                    className="rounded-md border border-xmr-border px-3 py-2 text-sm hover:bg-white/5"
                    onClick={async () => {
                      const addr = payoutAddr.trim();
                      if (!addr) {
                        showToast("error", "Buyer payout address required before prepare.");
                        return;
                      }
                      setBusy(true);
                      try {
                        const out = await prepareMultisigRelease(tradeId, {
                          buyer_payout_address: addr,
                          maker_return_address: makerReturn.trim() || undefined,
                          taker_return_address: takerReturn.trim() || undefined,
                        });
                        setTrade(out.trade);
                        showToast("success", "Unsigned multisig transaction prepared.");
                      } catch (e) {
                        showToast("error", e instanceof Error ? e.message : "Prepare failed");
                      } finally {
                        setBusy(false);
                      }
                    }}
                  >
                    {busy ? "Preparing…" : "1. Prepare"}
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    className="rounded-md border border-xmr-border px-3 py-2 text-sm hover:bg-white/5"
                    onClick={async () => {
                      setBusy(true);
                      try {
                        const out = await signMultisigRelease(tradeId, {
                          party: "buyer",
                          tx_data_hex: buyerSignHex.trim() || null,
                        });
                        setTrade(out.trade);
                        showToast("success", "Buyer multisig signature recorded.");
                      } catch (e) {
                        showToast("error", e instanceof Error ? e.message : "Buyer sign step failed");
                      } finally {
                        setBusy(false);
                      }
                    }}
                  >
                    {busy ? "Signing…" : "2. Buyer sign"}
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    className="rounded-md border border-xmr-border px-3 py-2 text-sm hover:bg-white/5"
                    onClick={async () => {
                      setBusy(true);
                      try {
                        const out = await signMultisigRelease(tradeId, {
                          party: "seller",
                          tx_data_hex: sellerSignHex.trim() || null,
                        });
                        setTrade(out.trade);
                        showToast("success", "Seller multisig signature recorded.");
                      } catch (e) {
                        showToast("error", e instanceof Error ? e.message : "Seller sign step failed");
                      } finally {
                        setBusy(false);
                      }
                    }}
                  >
                    {busy ? "Signing…" : "3. Seller sign"}
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    className="rounded-md bg-xmr-accent px-3 py-2 text-sm font-medium text-black"
                    onClick={async () => {
                      setBusy(true);
                      try {
                        const t = await submitMultisigRelease(tradeId);
                        setTrade(t);
                        showToast("success", "Escrow released. Transaction submitted.");
                        setShowRelease(false);
                        setPayoutAddr("");
                        setMakerReturn("");
                        setTakerReturn("");
                        setBuyerSignHex("");
                        setSellerSignHex("");
                      } catch (e) {
                        showToast("error", e instanceof Error ? e.message : "Submit failed");
                      } finally {
                        setBusy(false);
                      }
                    }}
                  >
                    {busy ? "Submitting…" : "4. Submit"}
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  disabled={busy}
                  className="rounded-md bg-xmr-accent px-3 py-2 text-sm font-medium text-black"
                  onClick={async () => {
                    const addr = payoutAddr.trim();
                    if (!addr) {
                      showToast("error", "Payout address required");
                      return;
                    }
                    const ok = await run(
                      () =>
                        releaseEscrow(tradeId, {
                          buyer_payout_address: addr,
                          maker_return_address: makerReturn.trim() || undefined,
                          taker_return_address: takerReturn.trim() || undefined,
                        }),
                      "Escrow released.",
                    );
                    if (ok) {
                      setShowRelease(false);
                      setPayoutAddr("");
                      setMakerReturn("");
                      setTakerReturn("");
                    }
                  }}
                >
                  {busy ? "Releasing…" : "Confirm release"}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {showDispute && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-4"
          onClick={() => setShowDispute(false)}
          role="presentation"
        >
          <div
            className="w-full max-w-md rounded-lg border border-xmr-border bg-xmr-panel p-4"
            onClick={(e) => e.stopPropagation()}
            role="presentation"
          >
            <h3 className="font-medium">Open dispute</h3>
            <textarea
              value={disputeReason}
              onChange={(e) => setDisputeReason(e.target.value)}
              rows={3}
              className="mt-3 w-full rounded-md border border-xmr-border bg-black/30 px-3 py-2 text-sm"
              placeholder="Reason"
            />
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" className="rounded-md border px-3 py-2 text-sm" onClick={() => setShowDispute(false)}>
                Cancel
              </button>
              <button
                type="button"
                disabled={busy}
                className="rounded-md bg-red-900/60 px-3 py-2 text-sm text-red-100"
                onClick={async () => {
                  const r = disputeReason.trim();
                  if (!r) {
                    showToast("error", "Reason required");
                    return;
                  }
                  const ok = await run(() => openDispute(tradeId, r), "Dispute opened.");
                  if (ok) {
                    setShowDispute(false);
                    setDisputeReason("");
                  }
                }}
              >
                Submit
              </button>
            </div>
          </div>
        </div>
      )}

      {showCancel && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-4"
          onClick={() => setShowCancel(false)}
          role="presentation"
        >
          <div
            className="w-full max-w-md rounded-lg border border-xmr-border bg-xmr-panel p-4"
            onClick={(e) => e.stopPropagation()}
            role="presentation"
          >
            <h3 className="font-medium">Collaborative cancel</h3>
            <p className="mt-2 text-xs text-xmr-muted">Uses your signed-in account id as actor_id.</p>
            <textarea
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              rows={2}
              className="mt-3 w-full rounded-md border border-xmr-border bg-black/30 px-3 py-2 text-sm"
              placeholder="Reason"
            />
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" className="rounded-md border px-3 py-2 text-sm" onClick={() => setShowCancel(false)}>
                Close
              </button>
              <button
                type="button"
                disabled={busy}
                className="rounded-md border border-xmr-border px-3 py-2 text-sm"
                onClick={async () => {
                  const actor = pseudonym.trim();
                  const r = cancelReason.trim();
                  if (!actor || !r) {
                    showToast("error", "Pseudonym and reason required");
                    return;
                  }
                  const ok = await run(() => cancelTrade(tradeId, { actor_id: actor, reason: r }), "Trade cancelled.");
                  if (ok) {
                    setShowCancel(false);
                    setCancelReason("");
                  }
                }}
              >
                Confirm cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
