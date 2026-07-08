"use client";

import { Check, X } from "lucide-react";
import { PageShell } from "@/components/primitives/PageShell";
import { Surface } from "@/components/primitives/Surface";
import { useIntegrity, useSyncStatus } from "@/lib/hooks/useVault";

function Chain({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className="flex items-center justify-between border-b border-hairline py-3 last:border-0">
      <span className="text-[15px] text-ink">{label}</span>
      <span
        className="inline-flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-widest"
        style={{ color: ok ? "var(--ink-soft)" : "var(--brass)" }}
      >
        {ok ? <Check size={13} /> : <X size={13} />}
        {ok ? "verified" : "broken"}
      </span>
    </div>
  );
}

/** The trust surface — tamper-evidence for both hash chains and the zero-knowledge sync relay. */
export default function Privacy() {
  const { data: integrity } = useIntegrity();
  const { data: sync } = useSyncStatus();

  return (
    <PageShell
      title="Yours, provably"
      description="Nova's memory is tamper-evident and on-device. Sync is zero-knowledge — the server only ever holds ciphertext it can't read."
    >
      <div className="flex flex-col gap-8">
        <Surface className="p-6">
          <p className="mb-2 font-mono text-[11px] uppercase tracking-widest text-ink-faint">
            tamper-evidence
          </p>
          {integrity ? (
            <>
              <Chain label="Memory audit chain" ok={integrity.audit_chain_ok} />
              <Chain label="Privacy deletion chain" ok={integrity.privacy_chain_ok} />
            </>
          ) : (
            <div className="h-16 rounded-md bg-hairline/30" />
          )}
        </Surface>

        <Surface className="p-6">
          <p className="mb-3 font-mono text-[11px] uppercase tracking-widest text-ink-faint">
            zero-knowledge sync
          </p>
          {sync ? (
            <div className="flex flex-col gap-2 text-[15px] text-ink">
              <div className="flex justify-between">
                <span className="text-ink-soft">Encrypted deltas held</span>
                <span className="font-mono">{sync.total_deltas}</span>
              </div>
              {Object.entries(sync.by_device).map(([device, count]) => (
                <div key={device} className="flex justify-between">
                  <span className="text-ink-soft capitalize">{device}</span>
                  <span className="font-mono">{count}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="h-16 rounded-md bg-hairline/30" />
          )}
          <p className="mt-4 text-sm leading-relaxed text-ink-soft">
            The server stores opaque ciphertext produced on your device. It never holds the key and
            never decrypts. Forgetting a memory issues a signed certificate and appends to the
            deletion chain above.
          </p>
        </Surface>
      </div>
    </PageShell>
  );
}
