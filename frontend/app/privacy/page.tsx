"use client";

import Link from "next/link";
import { Check, TriangleAlert } from "lucide-react";
import { Page } from "@/components/ui/Page";
import { Button } from "@/components/ui/Button";
import { Skeleton, Trouble } from "@/components/ui/States";
import { useIntegrity, useSyncStatus } from "@/lib/hooks/useVault";

const PROMISES = [
  {
    line: "It stays on this computer.",
    detail:
      "Nova thinks using models running on your own machine. Nothing you say is sent to a company to be answered, stored, or learned from.",
  },
  {
    line: "It can’t be quietly changed.",
    detail:
      "Every entry in Nova’s records is sealed to the one before it, like numbered pages stitched into a notebook. Tear one out or rewrite it and the seals stop matching — and the check below would catch it.",
  },
  {
    line: "You can make it forget.",
    detail:
      "Open any memory and ask Nova to forget it. It’s erased, and you get a signed receipt proving it happened.",
  },
];

function Verdict({ ok, name }: { ok: boolean; name: string }) {
  return (
    <li className="flex items-start gap-3">
      <span
        className={`mt-0.5 grid size-7 shrink-0 place-items-center cut-sm ${ok ? "bg-earned text-[#10302e]" : "bg-danger text-accent-ink"}`}
      >
        {ok ? (
          <Check size={16} aria-hidden />
        ) : (
          <TriangleAlert size={16} aria-hidden />
        )}
      </span>
      <span>
        <span className="block">{name}</span>
        <span className="block text-[length:var(--text-small)] text-ink-soft">
          {ok
            ? "Unchanged since it was written."
            : "Doesn’t add up — something may have been altered."}
        </span>
      </span>
    </li>
  );
}

/** Privacy: what's promised, and live proof of it. */
export default function Privacy() {
  const integrity = useIntegrity();
  const sync = useSyncStatus();
  const devices = Object.entries(sync.data?.by_device ?? {});

  return (
    <Page
      title="Privacy"
      intro="What Nova promises about your data, and a live check that it holds."
    >
      <ul className="mb-20 grid gap-10 lg:grid-cols-3">
        {PROMISES.map((p) => (
          <li key={p.line}>
            <h2 className="font-display text-[length:var(--text-title)] leading-[1.1]">
              {p.line}
            </h2>
            <p className="read mt-3 text-ink-soft">{p.detail}</p>
          </li>
        ))}
      </ul>

      <div className="grid gap-16 lg:grid-cols-2">
        <section aria-labelledby="altered">
          <h2 id="altered" className="mb-5 text-[length:var(--text-title)]">
            Has anything been altered?
          </h2>
          {integrity.isLoading ? (
            <Skeleton lines={3} />
          ) : integrity.isError || !integrity.data ? (
            <Trouble
              what="The check couldn’t run just now."
              onRetry={() => integrity.refetch()}
            />
          ) : (
            <>
              <ul className="flex flex-col gap-5">
                <Verdict
                  ok={integrity.data.audit_chain_ok}
                  name="Nova’s record of what it remembers"
                />
                <Verdict
                  ok={integrity.data.privacy_chain_ok}
                  name="The record of what you’ve asked it to forget"
                />
                <Verdict
                  ok={integrity.data.safety_chain_ok}
                  name="The record of times Nova checked in on you"
                />
              </ul>
              <p className="read mt-6">
                {integrity.data.status === "INTACT"
                  ? "Everything checks out."
                  : "Something doesn’t match. Your records may have been changed outside of Nova."}
              </p>
              <Button
                variant="quiet"
                className="mt-5"
                onClick={() => integrity.refetch()}
                disabled={integrity.isFetching}
              >
                {integrity.isFetching ? "Checking…" : "Check again"}
              </Button>
            </>
          )}
        </section>

        <section aria-labelledby="devices">
          <h2 id="devices" className="mb-5 text-[length:var(--text-title)]">
            Your other devices
          </h2>
          <p className="read mb-5 text-ink-soft">
            If you use Nova on more than one device, they can keep each other up
            to date. The go-between only ever holds scrambled data it can’t read
            — only your devices hold the key.
          </p>
          {sync.isLoading ? (
            <Skeleton lines={2} />
          ) : sync.isError ? (
            <Trouble
              what="Device sync status couldn’t be loaded just now."
              onRetry={() => sync.refetch()}
            />
          ) : devices.length === 0 ? (
            <p className="read">
              No other devices are connected, so nothing is being copied
              anywhere.
            </p>
          ) : (
            <ul className="flex flex-col gap-3">
              {devices.map(([id, n]) => (
                <li key={id} className="read">
                  Device <span className="font-medium">{id.slice(0, 8)}</span> ·{" "}
                  {n} {n === 1 ? "update" : "updates"} shared
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <p className="read mt-20 max-w-2xl">
        Want something gone?{" "}
        <Link
          href="/memory"
          className="text-accent underline underline-offset-4"
        >
          Open Memory
        </Link>{" "}
        and ask Nova to forget it.
      </p>
    </Page>
  );
}
