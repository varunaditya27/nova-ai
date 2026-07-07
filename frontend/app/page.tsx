"use client";

// TEMPORARY token/verification swatch — replaced by the real Threshold in Task 9.
import { useTheme } from "@/components/ThemeProvider";

export default function Home() {
  const { theme, toggle } = useTheme();
  return (
    <main className="mx-auto max-w-2xl px-8 py-24">
      <p className="font-mono text-xs uppercase tracking-widest text-ink-faint">
        token check · {theme}
      </p>
      <h1 className="font-display mt-4 text-5xl text-ink">
        Intelligence that remembers.
      </h1>
      <p className="mt-4 text-lg text-ink-soft">
        It notices. It continues. Numbers stay tabular: 1,204,096.
      </p>

      <div className="mt-10 grid grid-cols-3 gap-3">
        {(["paper", "surface", "raised", "ink", "ink-soft", "hairline", "brass"] as const).map(
          (t) => (
            <div
              key={t}
              className="rounded-md border border-hairline p-4"
              style={{ background: `var(--${t})` }}
            >
              <span className="font-mono text-xs text-ink-faint mix-blend-difference">{t}</span>
            </div>
          )
        )}
      </div>

      <button
        onClick={toggle}
        className="mt-10 rounded-md border border-hairline bg-surface px-4 py-2 text-sm text-ink transition-colors hover:bg-raised"
      >
        toggle theme
      </button>
    </main>
  );
}
