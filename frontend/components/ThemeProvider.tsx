"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

type Theme = "light" | "dark";

const ThemeContext = createContext<{ theme: Theme; toggle: () => void }>({
  theme: "light",
  toggle: () => {},
});

/**
 * Reads the theme the no-flash script already stamped onto <html data-theme> and exposes a
 * toggle. The initial paint is correct before hydration; this only wires up the switch.
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    const current = document.documentElement.getAttribute("data-theme");
    if (current === "dark" || current === "light") setTheme(current);
  }, []);

  const toggle = useCallback(() => {
    setTheme((prev) => {
      const next: Theme = prev === "light" ? "dark" : "light";
      document.documentElement.setAttribute("data-theme", next);
      try {
        localStorage.setItem("nova-theme", next);
      } catch {
        /* private mode — ignore */
      }
      return next;
    });
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, toggle }}>{children}</ThemeContext.Provider>
  );
}

export const useTheme = () => useContext(ThemeContext);

/**
 * Inline, render-blocking script: stamps data-theme from localStorage (or system preference)
 * before first paint so a dark-mode visitor never sees an ivory flash. Injected verbatim in
 * <head> by the root layout.
 */
export const themeNoFlashScript = `(function(){try{var t=localStorage.getItem('nova-theme');if(t!=='light'&&t!=='dark'){t=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}document.documentElement.setAttribute('data-theme',t);}catch(e){document.documentElement.setAttribute('data-theme','light');}})();`;
