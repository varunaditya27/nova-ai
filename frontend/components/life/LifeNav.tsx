"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";

const TABS = [
  { href: "/life", label: "Timeline" },
  { href: "/life/calendar", label: "Calendar" },
  { href: "/life/museum", label: "Museum" },
];

/** Segmented sub-nav across the three Life lenses. */
export function LifeNav() {
  const pathname = usePathname();
  return (
    <nav className="mb-8 inline-flex gap-1 rounded-md border border-hairline bg-surface p-1">
      {TABS.map((tab) => {
        const active = pathname === tab.href;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={cn(
              "rounded-sm px-3 py-1.5 text-sm transition-colors",
              active ? "bg-raised text-ink" : "text-ink-soft hover:text-ink"
            )}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
