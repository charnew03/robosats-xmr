import { NavLink } from "react-router-dom";
import { useProfile } from "../context/ProfileContext";
import { Avatar } from "./Avatar";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-2 text-sm font-medium transition-colors ${
    isActive ? "bg-xmr-accent text-black" : "text-xmr-muted hover:bg-white/5 hover:text-xmr-text"
  }`;

export function NavBar() {
  const { pseudonym, setPseudonym } = useProfile();

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

        <div className="flex w-full min-w-[200px] flex-1 items-center gap-2 sm:w-auto sm:flex-initial sm:justify-end">
          <Avatar pseudonym={pseudonym || "?"} size="sm" />
          <input
            type="text"
            value={pseudonym}
            onChange={(e) => setPseudonym(e.target.value)}
            placeholder="Your pseudonym"
            className="min-w-0 flex-1 rounded-md border border-xmr-border bg-black/30 px-2 py-1.5 font-mono text-xs sm:max-w-[200px]"
            autoComplete="off"
            spellCheck={false}
          />
        </div>
      </div>
    </header>
  );
}
