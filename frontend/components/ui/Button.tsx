"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "quiet" | "text" | "danger";

/*
 * Buttons are rectangles with Nova's dog-eared corner, never pills. A primary button fills with ink
 * from the left on hover, as a page turning; the arrow, when there is one, leans forward.
 */
const base =
  "group relative isolate inline-flex min-h-12 items-center justify-center gap-3 overflow-hidden px-7 text-[length:var(--text-body)] font-medium transition-colors duration-300 active:translate-y-px disabled:opacity-50";

const wipe =
  "before:absolute before:inset-0 before:-z-10 before:origin-left before:scale-x-0 before:transition-transform before:duration-500 before:ease-[cubic-bezier(0.16,1,0.3,1)] hover:before:scale-x-100 disabled:before:hidden";

const variants: Record<Variant, string> = {
  primary: `fold-sm bg-accent text-accent-ink before:bg-ink hover:text-ground ${wipe}`,
  quiet: `fold-sm bg-sunk text-ink before:bg-ink hover:text-ground ${wipe}`,
  text: "min-h-11 px-0 text-accent underline decoration-2 underline-offset-[6px] hover:decoration-[3px]",
  danger: `fold-sm bg-danger text-accent-ink before:bg-ink hover:text-ground ${wipe}`,
};

const Arrow = () => (
  <ArrowRight
    aria-hidden
    size={18}
    className="transition-transform duration-300 group-hover:translate-x-1"
  />
);

export function Button({
  variant = "primary",
  arrow = false,
  className,
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  arrow?: boolean;
}) {
  return (
    <button
      className={cn(base, variants[variant], className)}
      {...props}
    >
      {children}
      {arrow && <Arrow />}
    </button>
  );
}

export function ButtonLink({
  href,
  variant = "primary",
  arrow = false,
  className,
  children,
}: {
  href: string;
  variant?: Variant;
  arrow?: boolean;
  className?: string;
  children: ReactNode;
}) {
  return (
    <Link href={href} className={cn(base, variants[variant], className)}>
      {children}
      {arrow && <Arrow />}
    </Link>
  );
}
