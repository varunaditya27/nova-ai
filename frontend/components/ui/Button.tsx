"use client";

import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "quiet" | "text" | "danger";

const base =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-full px-6 text-[length:var(--text-body)] font-medium transition-[background-color,color,transform] duration-200 active:translate-y-px disabled:opacity-50";

const variants: Record<Variant, string> = {
  primary: "bg-accent text-accent-ink hover:brightness-110",
  quiet: "bg-sunk text-ink hover:bg-raised",
  text: "px-2 text-accent underline decoration-2 underline-offset-4 hover:decoration-4",
  danger: "bg-danger text-accent-ink hover:brightness-110",
};

export function Button({
  variant = "primary",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return <button className={cn(base, variants[variant], className)} {...props} />;
}

export function ButtonLink({
  href,
  variant = "primary",
  className,
  children,
}: {
  href: string;
  variant?: Variant;
  className?: string;
  children: ReactNode;
}) {
  return (
    <Link href={href} className={cn(base, variants[variant], className)}>
      {children}
    </Link>
  );
}
