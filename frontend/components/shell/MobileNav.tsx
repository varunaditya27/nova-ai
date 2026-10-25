"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Ellipsis } from "lucide-react";
import { Sheet } from "@/components/ui/Sheet";
import { ALL_NAV, NAV, TABS, isActive } from "@/lib/nav";
import { usePendingTools } from "@/lib/hooks/useTools";
import { cn } from "@/lib/cn";
import { Controls } from "./Controls";
import { Pulse } from "./Pulse";
import { useCommandMenu } from "./CommandMenu";

/** The phone spine: four things you reach for most, and everything else behind "More". Flat, full-width. */
export function MobileNav() {
  const pathname = usePathname();
  const [more, setMore] = useState(false);
  const menu = useCommandMenu();
  const errands = usePendingTools().data?.length ?? 0;
  const inMore = !TABS.some((t) => isActive(pathname, t.href)) && ALL_NAV.some((i) => isActive(pathname, i.href));

  return (
    <>
      <nav
        aria-label="Main"
        className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 bg-surface px-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] pt-2 lg:hidden"
      >
        {TABS.map((item) => {
          const active = isActive(pathname, item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex min-h-14 flex-col items-center justify-center gap-0.5 rounded-2xl text-[length:var(--text-small)]",
                active ? "bg-raised text-ink" : "text-ink-soft"
              )}
            >
              <Icon size={20} aria-hidden className={active ? "text-accent" : undefined} />
              {item.label}
            </Link>
          );
        })}
        <button
          onClick={() => setMore(true)}
          className={cn(
            "relative flex min-h-14 flex-col items-center justify-center gap-0.5 rounded-2xl text-[length:var(--text-small)]",
            inMore ? "bg-raised text-ink" : "text-ink-soft"
          )}
        >
          <Ellipsis size={20} aria-hidden className={inMore ? "text-accent" : undefined} />
          More
          {errands > 0 && <span aria-label={`${errands} errands waiting`} className="absolute right-4 top-2 size-2.5 rounded-full bg-accent" />}
        </button>
      </nav>

      <Sheet open={more} onClose={() => setMore(false)} title="Everything else">
        <button
          onClick={() => {
            setMore(false);
            menu.open();
          }}
          className="mb-5 min-h-11 rounded-full bg-sunk px-5 text-left text-ink-soft"
        >
          Jump to a page, or search…
        </button>
        <nav aria-label="All pages" className="flex flex-col gap-5">
          {NAV.map((group, gi) => (
            <div key={gi}>
              {group.title && <p className="mb-1.5 text-[length:var(--text-small)] text-mute">{group.title}</p>}
              <ul className="flex flex-col gap-0.5">
                {group.items.map((item) => (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      onClick={() => setMore(false)}
                      aria-current={isActive(pathname, item.href) ? "page" : undefined}
                      className={cn(
                        "block rounded-2xl px-3 py-2.5",
                        isActive(pathname, item.href) ? "bg-sunk" : "hover:bg-sunk"
                      )}
                    >
                      <span className="block">{item.label}</span>
                      <span className="block text-[length:var(--text-small)] text-ink-soft">{item.about}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
        <div className="mt-8 flex flex-col gap-4 rounded-2xl bg-sunk p-4">
          <Pulse />
          <Controls />
        </div>
      </Sheet>
    </>
  );
}
