"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { SmoothScroll } from "@/components/brand/SmoothScroll";
import { CommandMenuProvider } from "./CommandMenu";
import { MobileNav } from "./MobileNav";
import { SideNav } from "./SideNav";

/** Routes that stand on their own — the front door has no navigation around it. */
const BARE = ["/welcome"];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const bare = BARE.includes(pathname);

  return (
    <CommandMenuProvider>
      <div className="grain" />
      <SmoothScroll enabled={pathname !== "/"} />
      <a href="#main" className="skip-link">
        Skip to the page
      </a>
      {!bare && <SideNav />}
      <main
        id="main"
        tabIndex={-1}
        className={
          bare ? "min-h-dvh" : "min-h-dvh pb-20 outline-none lg:ml-72 lg:pb-0"
        }
      >
        {children}
      </main>
      {!bare && <MobileNav />}
    </CommandMenuProvider>
  );
}
