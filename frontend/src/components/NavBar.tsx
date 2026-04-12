import { NavLink } from "react-router-dom";
import { useProfile } from "../context/ProfileContext";
import { shortId } from "../lib/format";
import { Avatar } from "./Avatar";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-2 text-sm font-medium transition-colors ${
    isActive ? "bg-xmr-accent text-black" : "text-xmr-muted hover:bg-white/5 hover:text-xmr-text"
  }`;

export function NavBar() {
  const { userId, isAuthenticated, logout } = useProfile();

  return (
    <header className="sticky top-0 z-40 border-b border-xmr-border bg-xmr-bg/95 backdrop-blur-sm">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <NavLink to="/" className="flex items-center gap-2 no-underline">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-xmr-accent text-sm font-bold text-black">
              XMR
            </span>
            <span className="font-semibold tracking-tight text-xmr-text">ROBOSATS XMR</span>
          </NavLink>
        </div>

        <nav className="flex flex-wrap items-center gap-1">
          <NavLink to="/" className={linkClass} end>
            Order book
          </NavLink>
          <NavLink to="/create-offer" className={linkClass}>
            Create offer
          </NavLink>
          <NavLink to="/dashboard" className={linkClass}>
            Dashboard
          </NavLink>
        </nav>

        <div className="flex w-full min-w-[200px] flex-1 flex-wrap items-center justify-end gap-2 sm:w-auto sm:flex-initial">
          {isAuthenticated && userId ? (
            <>
              <Avatar pseudonym={userId} size="sm" />
              <span className="font-mono text-xs text-xmr-muted" title={userId}>
                {shortId(userId, 8, 6)}
              </span>
              <button
                type="button"
                onClick={() => logout()}
                className="rounded-md border border-xmr-border px-2 py-1 text-xs hover:bg-white/5"
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink
                to="/login"
                className="rounded-md border border-xmr-border px-3 py-1.5 text-xs hover:bg-white/5"
              >
                Log in
              </NavLink>
              <NavLink
                to="/register"
                className="rounded-md bg-xmr-accent px-3 py-1.5 text-xs font-semibold text-black hover:bg-xmr-accentSoft"
              >
                Create account
              </NavLink>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
