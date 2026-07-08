"use client";

import { ShieldAlert, ShieldCheck } from "lucide-react";
import { useIntegrity } from "@/lib/hooks/useVault";

/** A quiet tamper-evidence badge — reads the Layer-2 + Layer-12 hash chains. */
export function IntegrityBadge() {
  const { data } = useIntegrity();
  if (!data) return null;
  const ok = data.status === "INTACT";
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-md border border-hairline px-2.5 py-1 font-mono text-[11px] uppercase tracking-widest"
      style={{ color: ok ? "var(--ink-soft)" : "var(--brass)" }}
    >
      {ok ? <ShieldCheck size={13} /> : <ShieldAlert size={13} />}
      {ok ? "chain intact" : "tamper detected"}
    </span>
  );
}
