import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

const STORAGE_KEY = "robosats_xmr_session_v1";

export type Session = {
  accessToken: string;
  userId: string;
};

type Ctx = {
  /** Seed-derived account id (opaque hex); use as maker_id / taker_id in API calls. */
  userId: string;
  accessToken: string | null;
  isAuthenticated: boolean;
  setSession: (session: Session) => void;
  logout: () => void;
  /** @deprecated Same as userId — kept so older screens can migrate incrementally. */
  pseudonym: string;
};

const ProfileContext = createContext<Ctx | null>(null);

function loadSession(): Session | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as unknown;
    if (
      typeof parsed === "object" &&
      parsed &&
      typeof (parsed as Session).accessToken === "string" &&
      typeof (parsed as Session).userId === "string"
    ) {
      return parsed as Session;
    }
  } catch {
    /* ignore */
  }
  return null;
}

export function ProfileProvider({ children }: { children: ReactNode }) {
  const [session, setSessionState] = useState<Session | null>(null);

  useEffect(() => {
    setSessionState(loadSession());
  }, []);

  const setSession = useCallback((s: Session) => {
    setSessionState(s);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
    } catch {
      /* ignore */
    }
  }, []);

  const logout = useCallback(() => {
    setSessionState(null);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
  }, []);

  const userId = session?.userId ?? "";
  const accessToken = session?.accessToken ?? null;

  const value = useMemo(
    () => ({
      userId,
      accessToken,
      isAuthenticated: Boolean(accessToken && userId),
      setSession,
      logout,
      pseudonym: userId,
    }),
    [userId, accessToken, setSession, logout],
  );

  return <ProfileContext.Provider value={value}>{children}</ProfileContext.Provider>;
}

export function useProfile(): Ctx {
  const ctx = useContext(ProfileContext);
  if (!ctx) throw new Error("useProfile must be used within ProfileProvider");
  return ctx;
}
