"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type LightMode = "auto" | "day" | "night";
export type Light = "dawn" | "day" | "dusk" | "night";

const KEY = "nova-light-mode";

/** The room's light for an hour of the local day. */
export function lightForHour(hour: number): Light {
  if (hour >= 5 && hour < 8) return "dawn";
  if (hour >= 8 && hour < 17) return "day";
  if (hour >= 17 && hour < 20) return "dusk";
  return "night";
}

export function resolveLight(mode: LightMode, now: Date = new Date()): Light {
  if (mode === "day") return "day";
  if (mode === "night") return "night";
  return lightForHour(now.getHours());
}

const Ctx = createContext<{
  mode: LightMode;
  light: Light;
  setMode: (m: LightMode) => void;
}>({ mode: "auto", light: "day", setMode: () => {} });

function readMode(): LightMode {
  try {
    const v = localStorage.getItem(KEY);
    if (v === "day" || v === "night" || v === "auto") return v;
  } catch {
    /* private mode */
  }
  return "auto";
}

/**
 * Keeps <html data-light> in step with the real hour (or the user's override). The first paint is
 * already right — the inline script below stamps it before hydration — so this only keeps it live.
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<LightMode>("auto");
  const [light, setLight] = useState<Light>("day");

  useEffect(() => {
    const m = readMode();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time client sync to the stored preference
    setModeState(m);
    const apply = () => {
      const next = resolveLight(m);
      setLight(next);
      document.documentElement.setAttribute("data-light", next);
    };
    apply();
    const id = window.setInterval(apply, 5 * 60 * 1000);
    return () => window.clearInterval(id);
  }, []);

  const setMode = useCallback((m: LightMode) => {
    setModeState(m);
    try {
      localStorage.setItem(KEY, m);
    } catch {
      /* ignore */
    }
    const next = resolveLight(m);
    setLight(next);
    document.documentElement.setAttribute("data-light", next);
  }, []);

  const value = useMemo(
    () => ({ mode, light, setMode }),
    [mode, light, setMode],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useLight = () => useContext(Ctx);

/** Inline, render-blocking: stamps data-light before first paint so the room never flashes. */
export const lightNoFlashScript = `(function(){try{var m=localStorage.getItem('${KEY}');var h=new Date().getHours();var l=h>=5&&h<8?'dawn':h>=8&&h<17?'day':h>=17&&h<20?'dusk':'night';if(m==='day')l='day';if(m==='night')l='night';document.documentElement.setAttribute('data-light',l);}catch(e){document.documentElement.setAttribute('data-light','day');}})();`;
