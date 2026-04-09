import { type FormEvent, useEffect, useState } from "react";
import type { Offer } from "../api";
import { takeOffer } from "../api";
import { formatFiatCurrency, formatPremium, formatXmr, shortId } from "../lib/format";

type Props = {
  offer: Offer | null;
  onClose: () => void;
  onSuccess: (tradeId: string) => void;
  onError: (message: string) => void;
};

export function TakeOfferModal({ offer, onClose, onSuccess, onError }: Props) {
  const [takerId, setTakerId] = useState("");
  const [confirmations, setConfirmations] = useState("10");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (!offer) return null;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const tid = takerId.trim();
    if (!tid) {
      onError("Enter your taker id (pseudonym).");
      return;
    }
    const rc = parseInt(confirmations, 10);
    if (Number.isNaN(rc) || rc < 1) {
      onError("Confirmations must be at least 1.");
      return;
    }
    setSubmitting(true);
    try {
      const trade = await takeOffer(offer.offer_id, {
        taker_id: tid,
        required_confirmations: rc,
      });
      onSuccess(trade.trade_id);
      onClose();
      setTakerId("");
    } catch (err) {
      onError(err instanceof Error ? err.message : "Take offer failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 p-4 sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="take-offer-title"
      onClick={onClose}
    >
      <div
        className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-lg border border-xmr-border bg-xmr-panel shadow-xl"
        onClick={(e) => e.stopPropagation()}
        role="presentation"
      >
        <div className="border-b border-xmr-border px-4 py-3">
          <h2 id="take-offer-title" className="text-lg font-semibold">
            Take offer
          </h2>
          <p className="mt-1 text-xs text-xmr-muted">
            You will fund escrow + bonds as taker. Use a pseudonym, not real name.
          </p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4 p-4">
          <div className="rounded-md border border-xmr-border bg-black/20 p-3 text-sm">
            <p className="text-xmr-muted">Amount</p>
            <p className="font-mono text-base">
              {formatXmr(offer.amount_xmr)} XMR · {formatPremium(offer.premium_pct)} ·{" "}
              {formatFiatCurrency(offer.fiat_currency)}
            </p>
            <p className="mt-2 text-xmr-muted">Payment</p>
            <p>{offer.payment_method}</p>
            <p className="mt-2 text-xmr-muted">Maker</p>
            <p className="font-mono text-xs">{shortId(offer.maker_id)}</p>
            <p className="mt-2 text-xs text-xmr-muted">
              Bonds: maker {formatXmr(offer.maker_bond_amount)} / taker{" "}
              {formatXmr(offer.taker_bond_amount)} XMR
            </p>
          </div>

          <label className="block text-sm">
            <span className="mb-1 block text-xmr-muted">Your taker id</span>
            <input
              value={takerId}
              onChange={(e) => setTakerId(e.target.value)}
              className="w-full rounded-md border border-xmr-border bg-black/30 px-3 py-2 font-mono text-sm"
              placeholder="e.g. taker-alice-01"
              autoComplete="off"
              disabled={submitting}
            />
          </label>

          <label className="block text-sm">
            <span className="mb-1 block text-xmr-muted">Required confirmations</span>
            <input
              type="number"
              min={1}
              value={confirmations}
              onChange={(e) => setConfirmations(e.target.value)}
              className="w-full rounded-md border border-xmr-border bg-black/30 px-3 py-2"
              disabled={submitting}
            />
          </label>

          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="rounded-md border border-xmr-border px-4 py-2 text-sm hover:bg-white/5"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-md bg-xmr-accent px-4 py-2 text-sm font-medium text-black hover:bg-xmr-accentSoft disabled:opacity-50"
            >
              {submitting ? "Taking…" : "Confirm take"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
