import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { loginWithSeed } from "../api";
import { Spinner } from "../components/Spinner";
import { useProfile } from "../context/ProfileContext";
import { useToast } from "../context/ToastContext";

export function LoginPage() {
  const navigate = useNavigate();
  const { setSession } = useProfile();
  const { showToast } = useToast();
  const [mnemonic, setMnemonic] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const m = mnemonic.trim();
    if (!m) {
      showToast("error", "Enter your 25-word seed phrase.");
      return;
    }
    setBusy(true);
    try {
      const tok = await loginWithSeed({ mnemonic: m });
      setSession({ accessToken: tok.access_token, userId: tok.user_id });
      setMnemonic("");
      showToast("success", "Signed in.");
      navigate("/");
    } catch (err) {
      showToast("error", err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-lg px-4 py-8 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-semibold">Log in with seed phrase</h1>
      <p className="mt-2 text-sm text-xmr-muted">
        Paste your 25-word Monero mnemonic. It is sent over HTTPS to the coordinator only for this request and is not
        stored on the server.
      </p>

      <form onSubmit={(e) => void onSubmit(e)} className="mt-8 space-y-4">
        <label className="block text-sm">
          <span className="mb-1 block text-xmr-muted">Seed phrase</span>
          <textarea
            value={mnemonic}
            onChange={(e) => setMnemonic(e.target.value)}
            rows={5}
            autoComplete="off"
            spellCheck={false}
            className="w-full rounded-md border border-xmr-border bg-black/30 px-3 py-2 font-mono text-xs leading-relaxed"
            placeholder="25 words separated by spaces…"
            disabled={busy}
          />
        </label>

        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-between sm:items-center">
          <p className="text-sm text-xmr-muted">
            New here?{" "}
            <Link className="text-xmr-accentSoft underline" to="/register">
              Create account
            </Link>
          </p>
          <button
            type="submit"
            disabled={busy}
            className="inline-flex items-center justify-center gap-2 rounded-md bg-xmr-accent px-6 py-2 text-sm font-semibold text-black hover:bg-xmr-accentSoft disabled:opacity-40"
          >
            {busy ? <Spinner className="h-4 w-4 border-black border-t-transparent" /> : null}
            Sign in
          </button>
        </div>
      </form>
    </main>
  );
}
