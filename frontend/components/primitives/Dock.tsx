"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { LayoutGrid, Moon, Sun, Volume2, VolumeX } from "lucide-react";
import { cn } from "@/lib/cn";
import { springs, useReducedMotionSafe } from "@/lib/motion";
import { useTheme } from "@/components/ThemeProvider";
import { useAcoustics } from "@/lib/hooks/useAcoustics";

const PRIMARY = [
  { href: "/desk", label: "Desk" },
  { href: "/chat", label: "Chat" },
];

// All the lenses live behind one "Lenses" popover so the dock stays lean as they multiply.
// `enabled: false` routes are built in later slices — shown dimmed as a promise.
const LENSES: { href: string; label: string; enabled: boolean }[] = [
  { href: "/life", label: "Life", enabled: true },
  { href: "/goals", label: "Goals", enabled: true },
  { href: "/relationship", label: "Relationship", enabled: true },
  { href: "/proactive", label: "Proactive", enabled: true },
  { href: "/memories", label: "Memories", enabled: true },
  { href: "/bookmarks", label: "Bookmarks", enabled: true },
  { href: "/milestones", label: "Milestones", enabled: true },
  { href: "/privacy", label: "Privacy", enabled: true },
  { href: "/admin", label: "Admin", enabled: true },
];

/** A floating Arc-style dock — Desk / Chat inline, every lens behind a Lenses popover. */
export function Dock() {
  const pathname = usePathname();
  const { theme, toggle } = useTheme();
  const { muted, setMuted } = useAcoustics();
  const { t } = useReducedMotionSafe();
  const [open, setOpen] = useState(false);

  if (pathname === "/") return null;

  const activeLens = LENSES.find((l) => pathname.startsWith(l.href));

  return (
    <nav className="pointer-events-none fixed inset-x-0 bottom-6 z-40 flex justify-center">
      <div className="pointer-events-auto relative flex items-center gap-1 rounded-lg border border-hairline bg-surface/90 p-1.5 backdrop-blur-sm">
        {PRIMARY.map((item) => {
          const active = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "relative rounded-md px-3 py-1.5 text-sm transition-colors",
                active ? "text-ink" : "text-ink-soft hover:text-ink"
              )}
            >
              {active && (
                <motion.span
                  layoutId="dock-active"
                  transition={t(springs.wake)}
                  className="absolute inset-0 rounded-md bg-raised"
                  style={{ boxShadow: "inset 0 1px 0 var(--wake)" }}
                />
              )}
              <span className="relative">{item.label}</span>
            </Link>
          );
        })}

        {/* Lenses popover */}
        <button
          onClick={() => setOpen((o) => !o)}
          aria-haspopup="menu"
          aria-expanded={open}
          aria-label="Lenses"
          className={cn(
            "relative flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors",
            activeLens ? "text-ink" : "text-ink-soft hover:text-ink"
          )}
        >
          {activeLens && (
            <motion.span
              layoutId="dock-active"
              transition={t(springs.wake)}
              className="absolute inset-0 rounded-md bg-raised"
              style={{ boxShadow: "inset 0 1px 0 var(--wake)" }}
            />
          )}
          <LayoutGrid size={14} className="relative" />
          <span className="relative">{activeLens ? activeLens.label : "Lenses"}</span>
        </button>

        <AnimatePresence>
          {open && (
            <>
              <button
                aria-label="Close"
                className="fixed inset-0 -z-10 cursor-default"
                onClick={() => setOpen(false)}
              />
              <motion.div
                initial={{ opacity: 0, y: 6, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 6, scale: 0.98 }}
                transition={t(springs.settle)}
                className="absolute bottom-[calc(100%+8px)] left-1/2 w-52 -translate-x-1/2 rounded-lg border border-hairline bg-raised p-1.5"
              >
                {LENSES.map((l) =>
                  l.enabled ? (
                    <Link
                      key={l.href}
                      href={l.href}
                      onClick={() => setOpen(false)}
                      className={cn(
                        "block rounded-md px-3 py-1.5 text-sm transition-colors",
                        pathname.startsWith(l.href)
                          ? "bg-surface text-ink"
                          : "text-ink-soft hover:bg-surface hover:text-ink"
                      )}
                    >
                      {l.label}
                    </Link>
                  ) : (
                    <span
                      key={l.href}
                      title="soon"
                      className="block cursor-default rounded-md px-3 py-1.5 text-sm text-ink-faint/60"
                    >
                      {l.label}
                    </span>
                  )
                )}
              </motion.div>
            </>
          )}
        </AnimatePresence>

        <span className="mx-1 h-5 w-px bg-hairline" aria-hidden />

        <button
          onClick={toggle}
          aria-label={theme === "dark" ? "Switch to daylight" : "Switch to night"}
          className="rounded-md p-2 text-ink-soft transition-colors hover:text-ink"
        >
          {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
        </button>
        <button
          onClick={() => setMuted(!muted)}
          aria-label={muted ? "Unmute acoustics" : "Mute acoustics"}
          className="rounded-md p-2 text-ink-soft transition-colors hover:text-ink"
        >
          {muted ? <VolumeX size={16} /> : <Volume2 size={16} />}
        </button>
      </div>
    </nav>
  );
}
