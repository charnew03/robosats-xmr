import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { registerConfirm, registerInit } from "../api";
import { Spinner } from "../components/Spinner";
import { useProfile } from "../context/ProfileContext";
import { useToast } from "../context/ToastContext";

export function RegisterPage() {
  const navigate = useNavigate();
  const { setSession } = useProfile();
  const { showToast } = useToast();
  const [seedShown, setSeedShown] = useState(false);
  const [busy, setBusy] = useState(false);
  const [mnemonic, setMnemonic] = useState("");
  const [setupToken, setSetupToken] = useState("");
  const [backedUp, setBackedUp] = useState(false);

  async function startCreate() {
    setBusy(true);
    try {
      const res = await registerInit();
      setMnemonic(res.mnemonic);
      setSetupToken(res.setup_token);
      setSeedShown(true);
    } catch (e) {
      showToast("error", e instanceof Error ? e.message : "Could not start registration");
    } finally {
      setBusy(false);
    }
  }

  async function confirmAccount() {
    if (!backedUp) {
      showToast("error", "Confirm that you have saved your seed phrase.");
      return;
    }
    setBusy(true);
    try {
      const tok = await registerConfirm({ setup_token: setupToken, mnemonic });
      setSession({ accessToken: tok.access_token, userId: tok.user_id });
      setMnemonic("");
      setSetupToken("");
      showToast("success", "Account created.");
      navigate("/");
    } catch (e) {
      showToast("error", e instanceof Error ? e.message : "Confirmation failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-lg px-4 py-8 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-semibold">Create account</h1>
      <p className="mt-2 text-sm text-xmr-muted">
        Accounts use a <strong className="text-xmr-text">25-word Monero seed phrase</strong>. The server never stores
        your seed; it only stores a one-way account id derived after you finish backup confirmation.
      </p>

      {!seedShown && (
        <div className="mt-8">
          <button
            type="button"
            onClick={() => void startCreate()}
            disabled={busy}
            className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-xmr-accent py-3 text-sm font-semibold text-black hover:bg-xmr-accentSoft disabled:opacity-40 sm:w-auto sm:px-8"
          >
            {busy ? <Spinner className="h-4 w-4 border-black border-t-transparent" /> : null}
            Generate new seed phrase
          </button>
          <p className="mt-4 text-sm text-xmr-muted">
            Already have a seed?{" "}
            <Link className="text-xmr-accentSoft underline" to="/login">
              Log in
            </Link>
          </p>
        </div>
      )}

      {seedShown && (
        <div className="mt-8 space-y-4">
          <div className="rounded-lg border border-amber-800/60 bg-amber-950/30 p-4 text-sm text-amber-50">
            <p className="font-semibold text-amber-100">Critical — read carefully</p>
            <p className="mt-2">
              This 25-word seed is your <strong>account password</strong>. Save it safely offline. If you lose it, you
              lose access to your account. Never share it; anyone with the seed controls your account.
            </p>
          </div>

          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-xmr-muted">Your seed phrase</p>
            <div className="rounded-md border border-xmr-border bg-black/40 p-3 font-mono text-xs leading-relaxed text-xmr-text">
              {mnemonic}
            </div>
            <button
              type="button"
              className="mt-2 text-sm text-xmr-accentSoft underline"
              onClick={() => void navigator.clipboard.writeText(mnemonic).then(() => showToast("success", "Copied."))}
            >
              Copy to clipboard
            </button>
          </div>

          <label className="flex cursor-pointer items-start gap-3 text-sm">
            <input
              type="checkbox"
              checked={backedUp}
              onChange={(e) => setBackedUp(e.target.checked)}
              className="mt-1"
            />
            <span>I have written down or otherwise securely stored this seed phrase.</span>
          </label>

          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <button
              type="button"
              onClick={() => {
                setMnemonic("");
                setSetupToken("");
                setBackedUp(false);
                setSeedShown(false);
              }}
              disabled={busy}
              className="rounded-md border border-xmr-border px-4 py-2 text-sm hover:bg-white/5 disabled:opacity-40"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => void confirmAccount()}
              disabled={!backedUp || busy}
              className="inline-flex items-center justify-center gap-2 rounded-md bg-xmr-accent px-4 py-2 text-sm font-semibold text-black hover:bg-xmr-accentSoft disabled:opacity-40"
            >
              {busy ? <Spinner className="h-4 w-4 border-black border-t-transparent" /> : null}
              Finish — create account
            </button>
          </div>
        </div>
      )}
    </main>
  );
}
