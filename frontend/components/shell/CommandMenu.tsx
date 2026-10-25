"use client";

import {
  createContext,
  useContext,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { CornerDownLeft, Search } from "lucide-react";
import { searchMemory, searchMessages } from "@/lib/api/client";
import { ALL_NAV } from "@/lib/nav";
import { springs, useReducedMotionSafe } from "@/lib/motion";
import { humanDay, relativeTime } from "@/lib/time";
import { cn } from "@/lib/cn";

const Ctx = createContext<{ open: () => void }>({ open: () => {} });
export const useCommandMenu = () => useContext(Ctx);

type Row = {
  key: string;
  title: string;
  hint: string;
  go: () => void;
  group: string;
};

function useDebounced<T>(value: T, ms = 250): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setV(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return v;
}

/**
 * "Jump to…" — one surface for going anywhere and finding anything. Pages are matched as you type;
 * your exact words are searched in the conversation, and the meaning of what you typed is searched
 * in Nova's memory ("the time I was scared"). Everything is reachable from the keyboard.
 */
export function CommandMenuProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { t } = useReducedMotionSafe();
  const [isOpen, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [cursor, setCursor] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const listId = useId();
  const term = useDebounced(q.trim());

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (!isOpen) return;
    input.current?.focus();
    const opener = document.activeElement as HTMLElement | null;
    return () => opener?.focus?.();
  }, [isOpen]);

  const words = useQuery({
    queryKey: ["cmd", "words", term],
    queryFn: () => searchMessages(term, { limit: 5 }),
    enabled: isOpen && term.length >= 2,
  });
  const meaning = useQuery({
    queryKey: ["cmd", "meaning", term],
    queryFn: () => searchMemory(term, 4),
    enabled: isOpen && term.length >= 3,
  });

  const close = () => {
    setOpen(false);
    setQ("");
    setCursor(0);
  };

  const rows: Row[] = useMemo(() => {
    const lower = q.trim().toLowerCase();
    const pages = ALL_NAV.filter(
      (p) =>
        !lower ||
        p.label.toLowerCase().includes(lower) ||
        p.about.toLowerCase().includes(lower),
    ).map(
      (p): Row => ({
        key: `p-${p.href}`,
        title: p.label,
        hint: p.about,
        group: "Go to",
        go: () => router.push(p.href),
      }),
    );
    const said = (words.data ?? []).map(
      (m): Row => ({
        key: `w-${m.message_id}`,
        title: m.content.length > 90 ? `${m.content.slice(0, 90)}…` : m.content,
        hint: `${m.role === "nova" ? "Nova said" : "You said"} · ${humanDay(m.created_at)}`,
        group: "In your conversation — your exact words",
        go: () => router.push(`/?m=${m.message_id}`),
      }),
    );
    const felt = (meaning.data ?? []).map(
      (m): Row => ({
        key: `m-${m.memory_id}`,
        title: m.summary,
        hint: `I remember · ${relativeTime(m.created_at)}`,
        group: "In my memory, by meaning",
        go: () => router.push(`/memory?open=${m.memory_id}`),
      }),
    );
    return [...pages, ...said, ...felt];
  }, [q, words.data, meaning.data, router]);

  const safeCursor = Math.min(cursor, Math.max(rows.length - 1, 0));
  const choose = (r: Row | undefined) => {
    if (!r) return;
    close();
    r.go();
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setCursor((c) => Math.min(c + 1, rows.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setCursor((c) => Math.max(c - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      choose(rows[safeCursor]);
    } else if (e.key === "Escape") {
      close();
    }
  };

  let lastGroup = "";
  return (
    <Ctx.Provider value={{ open: () => setOpen(true) }}>
      {children}
      <AnimatePresence>
        {isOpen && (
          <div className="fixed inset-0 z-[70] flex items-start justify-center px-4 pt-[12vh]">
            <motion.button
              aria-label="Close"
              className="absolute inset-0 cursor-default bg-ink/45"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={close}
            />
            <motion.div
              role="dialog"
              aria-modal="true"
              aria-label="Jump to"
              className="floating relative w-full max-w-2xl overflow-hidden rounded-[3px]"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              transition={t(springs.settle)}
            >
              <div className="flex items-center gap-3 bg-sunk px-6 py-4">
                <Search
                  size={20}
                  className="shrink-0 text-ink-soft"
                  aria-hidden
                />
                <input
                  ref={input}
                  value={q}
                  onChange={(e) => {
                    setQ(e.target.value);
                    setCursor(0);
                  }}
                  onKeyDown={onKeyDown}
                  role="combobox"
                  aria-expanded="true"
                  aria-controls={listId}
                  aria-activedescendant={
                    rows[safeCursor] ? `${listId}-${safeCursor}` : undefined
                  }
                  placeholder="Go somewhere, or ask me to find a moment…"
                  className="min-h-9 w-full bg-transparent text-[length:var(--text-read)] outline-none placeholder:text-mute"
                />
              </div>
              <ul
                id={listId}
                role="listbox"
                className="max-h-[52vh] overflow-y-auto px-3 py-3"
              >
                {rows.length === 0 && (
                  <li className="px-4 py-8 text-center text-ink-soft">
                    I can’t find “{q}”. Try other words, or describe the moment: “the night I couldn’t sleep”.
                  </li>
                )}
                {rows.map((r, i) => {
                  const header = r.group !== lastGroup;
                  lastGroup = r.group;
                  return (
                    <li key={r.key} role="presentation">
                      {header && (
                        <p className="px-4 pb-1 pt-3 text-[length:var(--text-small)] text-mute">
                          {r.group}
                        </p>
                      )}
                      <button
                        id={`${listId}-${i}`}
                        role="option"
                        aria-selected={i === safeCursor}
                        onMouseEnter={() => setCursor(i)}
                        onClick={() => choose(r)}
                        className={cn(
                          "flex w-full items-center justify-between gap-4 px-4 py-3 text-left",
                          i === safeCursor ? "bg-sunk" : "bg-transparent",
                        )}
                      >
                        <span className="min-w-0">
                          <span className="block truncate">{r.title}</span>
                          <span className="block truncate text-[length:var(--text-small)] text-ink-soft">
                            {r.hint}
                          </span>
                        </span>
                        {i === safeCursor && (
                          <CornerDownLeft
                            size={16}
                            className="shrink-0 text-ink-soft"
                            aria-hidden
                          />
                        )}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </Ctx.Provider>
  );
}
