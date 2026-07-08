"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { play as playSound, resume, type SoundName } from "@/lib/acoustics/player";

type AcousticsApi = {
  play: (name: SoundName) => void;
  muted: boolean;
  setMuted: (m: boolean) => void;
};

const AcousticsContext = createContext<AcousticsApi>({
  play: () => {},
  muted: true,
  setMuted: () => {},
});

const STORAGE_KEY = "nova-muted";

function initialMuted(): boolean {
  if (typeof window === "undefined") return true;
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "true") return true;
    if (stored === "false") return false;
  } catch {
    /* ignore */
  }
  // No stored preference: honour reduced-motion by defaulting to silence.
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function AcousticsProvider({ children }: { children: ReactNode }) {
  const [muted, setMutedState] = useState(true);
  const openedRef = useRef(false);

  // Resolve the real initial value after mount (SSR-safe), then arm the first-gesture chime.
  useEffect(() => {
    const start = initialMuted();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time client-only preference read (SSR-safe default avoids a hydration mismatch)
    setMutedState(start);

    const onFirstGesture = () => {
      resume();
      if (!openedRef.current && !initialMuted()) {
        openedRef.current = true;
        playSound("open");
      }
      window.removeEventListener("pointerdown", onFirstGesture);
      window.removeEventListener("keydown", onFirstGesture);
    };
    window.addEventListener("pointerdown", onFirstGesture, { once: false });
    window.addEventListener("keydown", onFirstGesture, { once: false });
    return () => {
      window.removeEventListener("pointerdown", onFirstGesture);
      window.removeEventListener("keydown", onFirstGesture);
    };
  }, []);

  const setMuted = useCallback((m: boolean) => {
    setMutedState(m);
    try {
      localStorage.setItem(STORAGE_KEY, String(m));
    } catch {
      /* ignore */
    }
    if (m) playSound("room-off");
  }, []);

  const play = useCallback(
    (name: SoundName) => {
      if (muted) return;
      playSound(name);
    },
    [muted]
  );

  return (
    <AcousticsContext.Provider value={{ play, muted, setMuted }}>
      {children}
    </AcousticsContext.Provider>
  );
}

export const useAcoustics = () => useContext(AcousticsContext);
