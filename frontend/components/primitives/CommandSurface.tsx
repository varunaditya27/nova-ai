"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Search } from "lucide-react";
import { cn } from "@/lib/cn";
import { springs, useReducedMotionSafe } from "@/lib/motion";

export type SearchKind = "keyword" | "semantic";

export type CommandResult = {
  id: string;
  title: string;
  subtitle?: string;
  when?: string;
};

/**
 * A ⌘K command surface — the only place search lives, so the thread is never cluttered. It opens on
 * ⌘K / Ctrl-K, toggles between deterministic keyword search and semantic ("the time I was scared")
 * search, and hands the chosen result back to the parent to jump the thread.
 */
export function CommandSurface({
  open,
  onOpenChange,
  runSearch,
  onSelect,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  runSearch: (kind: SearchKind, q: string) => Promise<CommandResult[]>;
  onSelect: (result: CommandResult, kind: SearchKind) => void;
}) {
  const { t } = useReducedMotionSafe();
  const [kind, setKind] = useState<SearchKind>("keyword");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CommandResult[]>([]);
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Global ⌘K / Ctrl-K toggle.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        onOpenChange(!open);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onOpenChange]);

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 10);
      return;
    }
    // Reset the palette on close — client-only UI state, reacting to the controlled `open` prop.
    /* eslint-disable react-hooks/set-state-in-effect */
    setQuery("");
    setResults([]);
    setActive(0);
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [open]);

  // Debounced search whenever the query or kind changes.
  useEffect(() => {
    if (!open) return;
    const q = query.trim();
    if (!q) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- clear stale results as the debounced query empties
      setResults([]);
      return;
    }
    let cancelled = false;
    const id = setTimeout(async () => {
      try {
        const r = await runSearch(kind, q);
        if (!cancelled) {
          setResults(r);
          setActive(0);
        }
      } catch {
        if (!cancelled) setResults([]);
      }
    }, 220);
    return () => {
      cancelled = true;
      clearTimeout(id);
    };
  }, [query, kind, open, runSearch]);

  const choose = useCallback(
    (r: CommandResult) => {
      onSelect(r, kind);
      onOpenChange(false);
    },
    [onSelect, kind, onOpenChange]
  );

  const onInputKey = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") onOpenChange(false);
    else if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter" && results[active]) {
      choose(results[active]);
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={t(springs.wake)}
          className="fixed inset-0 z-50 flex items-start justify-center bg-ink/10 px-4 pt-[18vh] backdrop-blur-[2px]"
          onClick={() => onOpenChange(false)}
        >
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.98 }}
            transition={t(springs.settle)}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-xl overflow-hidden rounded-lg border border-hairline bg-raised"
          >
            <div className="flex items-center gap-2 border-b border-hairline px-4">
              <Search size={16} className="text-ink-faint" />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={onInputKey}
                placeholder={
                  kind === "keyword" ? "Search the conversation…" : "Ask by feeling…"
                }
                className="flex-1 bg-transparent py-3.5 text-[15px] text-ink outline-none placeholder:text-ink-faint"
              />
              <div className="flex gap-0.5 text-[11px]">
                {(["keyword", "semantic"] as const).map((k) => (
                  <button
                    key={k}
                    onClick={() => setKind(k)}
                    className={cn(
                      "rounded-sm px-2 py-1 transition-colors",
                      kind === k
                        ? "bg-surface text-ink"
                        : "text-ink-faint hover:text-ink-soft"
                    )}
                  >
                    {k}
                  </button>
                ))}
              </div>
            </div>

            {results.length > 0 && (
              <ul className="max-h-80 overflow-y-auto py-1.5">
                {results.map((r, i) => (
                  <li key={r.id}>
                    <button
                      onMouseEnter={() => setActive(i)}
                      onClick={() => choose(r)}
                      className={cn(
                        "flex w-full items-baseline gap-3 px-4 py-2 text-left",
                        i === active ? "bg-surface" : ""
                      )}
                    >
                      <span className="flex-1 truncate text-sm text-ink">{r.title}</span>
                      {r.when && (
                        <span className="shrink-0 font-mono text-[11px] text-ink-faint">
                          {r.when}
                        </span>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}

            {query.trim() && results.length === 0 && (
              <p className="px-4 py-6 text-center text-sm text-ink-faint">
                Nothing surfaced. Nova hasn&apos;t heard of that yet.
              </p>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
