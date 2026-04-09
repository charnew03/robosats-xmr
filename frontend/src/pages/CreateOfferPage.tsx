import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createOffer } from "../api";
import { Spinner } from "../components/Spinner";
import { useProfile } from "../context/ProfileContext";
import { useToast } from "../context/ToastContext";
import { saveOfferNote } from "../lib/offerNoteStorage";

type ListingSide = "sell_xmr" | "buy_xmr";

export function CreateOfferPage() {
  const navigate = useNavigate();
  const { pseudonym, setPseudonym } = useProfile();
  const { showToast } = useToast();
  const [side, setSide] = useState<ListingSide>("sell_xmr");
  const [amountXmr, setAmountXmr] = useState("0.5");
  const [premiumPct, setPremiumPct] = useState("0");
  const [fiatCurrency, setFiatCurrency] = useState("USD");
  const [paymentMethod, setPaymentMethod] = useState("SEPA");
  const [makerBond, setMakerBond] = useState("0.02");
  const [takerBond, setTakerBond] = useState("0.02");
  const [minAmount, setMinAmount] = useState("");
  const [maxAmount, setMaxAmount] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (side === "buy_xmr") {
      showToast("error", "Buy-side maker offers are not in the API yet. Choose Sell XMR.");
      return;
    }
    const makerId = pseudonym.trim();
    if (!makerId) {
      showToast("error", "Set your pseudonym in the header (maker id).");
      return;
    }
    const amount = Number(amountXmr);
    if (Number.isNaN(amount) || amount <= 0) {
      showToast("error", "Invalid XMR amount.");
      return;
    }
    const minA = minAmount.trim() ? Number(minAmount) : null;
    const maxA = maxAmount.trim() ? Number(maxAmount) : null;
    if (minA !== null && !Number.isNaN(minA) && amount < minA) {
      showToast("error", "Amount is below your stated min (client check).");
      return;
    }
    if (maxA !== null && !Number.isNaN(maxA) && amount > maxA) {
      showToast("error", "Amount is above your stated max (client check).");
      return;
    }
    const prem = Number(premiumPct);
    if (Number.isNaN(prem)) {
      showToast("error", "Invalid premium.");
      return;
    }
    const mb = Number(makerBond);
    const tb = Number(takerBond);
    if (Number.isNaN(mb) || mb <= 0 || Number.isNaN(tb) || tb <= 0) {
      showToast("error", "Bonds must be positive numbers.");
      return;
    }
    const fiat = fiatCurrency.trim().toUpperCase();
    if (fiat.length < 2) {
      showToast("error", "Fiat currency code is too short.");
      return;
    }
    const pay = paymentMethod.trim();
    if (!pay) {
      showToast("error", "Payment method is required.");
      return;
    }

    setSubmitting(true);
    try {
      const offer = await createOffer({
        maker_id: makerId,
        amount_xmr: amount,
        premium_pct: prem,
        fiat_currency: fiat,
        payment_method: pay,
        maker_bond_amount_xmr: mb,
        taker_bond_amount_xmr: tb,
      });
      saveOfferNote(offer.offer_id, description);
      showToast("success", "Offer published.");
      navigate("/");
    } catch (err) {
      showToast("error", err instanceof Error ? err.message : "Create offer failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-xl px-4 py-8 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-semibold">Create offer</h1>
      <p className="mt-2 text-sm text-xmr-muted">
        You are the <strong className="text-xmr-text">maker</strong>. Use the same pseudonym as in the top bar, or
        edit it below.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <label className="block text-sm">
          <span className="mb-1 block text-xmr-muted">Listing side</span>
          <select
            value={side}
            onChange={(e) => setSide(e.target.value as ListingSide)}
            className="w-full rounded-md border border-xmr-border bg-black/20 px-3 py-2"
          >
            <option value="sell_xmr">Sell XMR for fiat (supported)</option>
            <option value="buy_xmr">Buy XMR with fiat (API not yet)</option>
          </select>
        </label>

        {side === "buy_xmr" && (
          <p className="rounded-md border border-amber-900/50 bg-amber-950/20 p-3 text-sm text-amber-100">
            This option is disabled for submit until the backend supports buy-side public offers. Use{" "}
            <strong>Sell XMR</strong> for now.
          </p>
        )}

        <label className="block text-sm">
          <span className="mb-1 block text-xmr-muted">Maker pseudonym</span>
          <input
            value={pseudonym}
            onChange={(e) => setPseudonym(e.target.value)}
            className="w-full rounded-md border border-xmr-border bg-black/30 px-3 py-2 font-mono text-sm"
            placeholder="same as navbar"
          />
        </label>

        <label className="block text-sm">
          <span className="mb-1 block text-xmr-muted">Amount (XMR)</span>
          <input
            type="number"
            min="0"
            step="0.0001"
            value={amountXmr}
            onChange={(e) => setAmountXmr(e.target.value)}
            className="w-full rounded-md border border-xmr-border bg-black/30 px-3 py-2"
          />
        </label>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block text-sm">
            <span className="mb-1 block text-xmr-muted">Min amount (XMR, optional)</span>
            <input
              type="number"
              min="0"
              step="0.0001"
              value={minAmount}
              onChange={(e) => setMinAmount(e.target.value)}
              className="w-full rounded-md border border-xmr-border bg-black/30 px-3 py-2"
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-xmr-muted">Max amount (XMR, optional)</span>
            <input
              type="number"
              min="0"
              step="0.0001"
              value={maxAmount}
              onChange={(e) => setMaxAmount(e.target.value)}
              className="w-full rounded-md border border-xmr-border bg-black/30 px-3 py-2"
            />
          </label>
        </div>
        <p className="text-xs text-xmr-muted">
          Min/max are client-side checks against the single listed amount. The API stores one size per offer.
        </p>

        <label className="block text-sm">
          <span className="mb-1 block text-xmr-muted">Premium (%)</span>
          <input
            type="number"
            step="0.1"
            value={premiumPct}
            onChange={(e) => setPremiumPct(e.target.value)}
            className="w-full rounded-md border border-xmr-border bg-black/30 px-3 py-2"
          />
        </label>

        <label className="block text-sm">
          <span className="mb-1 block text-xmr-muted">Fiat currency</span>
          <input
            value={fiatCurrency}
            onChange={(e) => setFiatCurrency(e.target.value)}
            className="w-full rounded-md border border-xmr-border bg-black/30 px-3 py-2 uppercase"
            maxLength={8}
          />
        </label>

        <label className="block text-sm">
          <span className="mb-1 block text-xmr-muted">Payment method</span>
          <input
            value={paymentMethod}
            onChange={(e) => setPaymentMethod(e.target.value)}
            className="w-full rounded-md border border-xmr-border bg-black/30 px-3 py-2"
          />
        </label>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block text-sm">
            <span className="mb-1 block text-xmr-muted">Maker bond (XMR)</span>
            <input
              type="number"
              min="0"
              step="0.001"
              value={makerBond}
              onChange={(e) => setMakerBond(e.target.value)}
              className="w-full rounded-md border border-xmr-border bg-black/30 px-3 py-2"
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-xmr-muted">Taker bond (XMR)</span>
            <input
              type="number"
              min="0"
              step="0.001"
              value={takerBond}
              onChange={(e) => setTakerBond(e.target.value)}
              className="w-full rounded-md border border-xmr-border bg-black/30 px-3 py-2"
            />
          </label>
        </div>

        <label className="block text-sm">
          <span className="mb-1 block text-xmr-muted">Description / terms (local only)</span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="w-full rounded-md border border-xmr-border bg-black/30 px-3 py-2 text-sm"
            placeholder="Stored in your browser for this offer id after publish — not sent to the server yet."
          />
        </label>

        <button
          type="submit"
          disabled={submitting || side === "buy_xmr"}
          className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-xmr-accent py-3 text-sm font-semibold text-black hover:bg-xmr-accentSoft disabled:opacity-40 sm:w-auto sm:px-8"
        >
          {submitting ? <Spinner className="h-4 w-4 border-black border-t-transparent" /> : null}
          Publish offer
        </button>
      </form>
    </main>
  );
}
