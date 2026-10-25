"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Search } from "lucide-react";
import { Ember } from "@/components/ui/Ember";
import { NAV, isActive } from "@/lib/nav";
import { usePendingTools } from "@/lib/hooks/useTools";
import { useAcoustics } from "@/lib/hooks/useAcoustics";
import { cn } from "@/lib/cn";
import { Controls } from "./Controls";
import { Pulse } from "./Pulse";
import { useCommandMenu } from "./CommandMenu";

/** The desktop spine: a flat tone column, plain labels, grouped by what you came here to do. */
export function SideNav() {
  const pathname = usePathname();
  const { play } = useAcoustics();
  const menu = useCommandMenu();
  const errands = usePendingTools().data?.length ?? 0;

  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-72 flex-col overflow-y-auto bg-surface px-5 py-5 lg:flex">
      <Link href="/" className="mb-4 flex items-center gap-3 px-2" aria-label="Nova — home">
        <Ember size={30} state="idle" className="text-accent" />
        <span className="font-display text-3xl leading-none">Nova</span>
      </Link>

      <button
        onClick={menu.open}
        className="mb-4 flex min-h-10 items-center justify-between gap-2 rounded-full bg-sunk px-4 text-left text-ink-soft hover:text-ink"
      >
        <span className="flex items-center gap-2">
          <Search size={16} aria-hidden /> Jump to…
        </span>
        <kbd className="text-[length:var(--text-small)] text-mute">Ctrl K</kbd>
      </button>

      <nav aria-label="Main" className="flex flex-1 flex-col gap-3">
        {NAV.map((group, gi) => (
          <div key={gi} className={cn(gi === NAV.length - 1 && "mt-auto")}>
            {group.title && <p className="mb-0.5 px-3 text-[length:var(--text-small)] text-mute">{group.title}</p>}
            <ul className="flex flex-col gap-0.5">
              {group.items.map((item) => {
                const active = isActive(pathname, item.href);
                const badge = item.href === "/errands" ? errands : 0;
                const Icon = item.icon;
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      aria-current={active ? "page" : undefined}
                      onClick={() => play("click")}
                      className={cn(
                        "flex min-h-10 items-center gap-3 rounded-2xl px-3 transition-colors duration-200",
                        active ? "bg-raised text-ink" : "text-ink-soft hover:bg-sunk hover:text-ink"
                      )}
                    >
                      <Icon size={18} aria-hidden className={active ? "text-accent" : undefined} />
                      <span className="flex-1">{item.label}</span>
                      {badge > 0 && (
                        <span
                          aria-label={`${badge} waiting for you`}
                          className="grid min-w-6 place-items-center rounded-full bg-accent px-2 text-[length:var(--text-small)] text-accent-ink"
                        >
                          {badge}
                        </span>
                      )}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      <div className="mt-3 flex flex-col gap-3 rounded-2xl bg-sunk p-3">
        <Pulse />
        <Controls />
      </div>
    </aside>
  );
}
