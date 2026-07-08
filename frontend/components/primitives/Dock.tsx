"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "motion/react";
import { Moon, Sun, Volume2, VolumeX } from "lucide-react";
import { cn } from "@/lib/cn";
import { springs, useReducedMotionSafe } from "@/lib/motion";
import { useTheme } from "@/components/ThemeProvider";
import { useAcoustics } from "@/lib/hooks/useAcoustics";

type Item = { href: string; label: string; enabled: boolean };

// Slice 1 ships Desk + Chat. The lens routes are present but dimmed ("soon") — a promise, not a
// dead end.
const ITEMS: Item[] = [
  { href: "/desk", label: "Desk", enabled: true },
  { href: "/chat", label: "Chat", enabled: true },
  { href: "/life", label: "Life", enabled: true },
  { href: "/memories", label: "Memories", enabled: false },
];

/** A floating Arc-style dock — not a sidebar. Fixed bottom-center; hosts nav + theme + mute. */
export function Dock() {
  const pathname = usePathname();
  const { theme, toggle } = useTheme();
  const { muted, setMuted } = useAcoustics();
  const { t } = useReducedMotionSafe();

  // Hidden on the marketing threshold — the front door has no chrome.
  if (pathname === "/") return null;

  return (
    <nav className="pointer-events-none fixed inset-x-0 bottom-6 z-40 flex justify-center">
      <div className="pointer-events-auto flex items-center gap-1 rounded-lg border border-hairline bg-surface/90 p-1.5 backdrop-blur-sm">
        {ITEMS.map((item) => {
          const active = pathname.startsWith(item.href);
          if (!item.enabled) {
            return (
              <span
                key={item.href}
                title="soon"
                className="cursor-default rounded-md px-3 py-1.5 text-sm text-ink-faint/60"
              >
                {item.label}
              </span>
            );
          }
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
