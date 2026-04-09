import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

const STORAGE_KEY = "robosats_xmr_pseudonym_v1";

type Ctx = {
  pseudonym: string;
  setPseudonym: (v: string) => void;
};

const ProfileContext = createContext<Ctx | null>(null);

export function ProfileProvider({ children }: { children: ReactNode }) {
  const [pseudonym, setPseudonymState] = useState("");

  useEffect(() => {
    try {
      const s = localStorage.getItem(STORAGE_KEY);
      if (s) setPseudonymState(s);
    } catch {
      /* ignore */
    }
  }, []);

  const setPseudonym = useCallback((v: string) => {
    const t = v.trim();
    setPseudonymState(t);
    try {
      if (t) localStorage.setItem(STORAGE_KEY, t);
      else localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
  }, []);

  const value = useMemo(() => ({ pseudonym, setPseudonym }), [pseudonym, setPseudonym]);

  return <ProfileContext.Provider value={value}>{children}</ProfileContext.Provider>;
}

export function useProfile(): Ctx {
  const ctx = useContext(ProfileContext);
  if (!ctx) throw new Error("useProfile must be used within ProfileProvider");
  return ctx;
}
