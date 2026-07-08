"use client";

import { PageShell } from "@/components/primitives/PageShell";
import { Surface } from "@/components/primitives/Surface";
import { useSafetyEvents } from "@/lib/hooks/useWellbeing";
import { relativeTime } from "@/lib/time";

// Raw tiers/scores never reach the UI as numbers — translate to plain, gentle language.
const TIER: Record<string, { label: string; weight: number }> = {
  tier_1: { label: "a flicker of concern", weight: 1 },
  tier_2: { label: "real concern", weight: 2 },
  tier_3: { label: "deep concern", weight: 3 },
};

/** Wellbeing — a transparent, calm log of moments Nova registered concern. Care, not surveillance. */
export default function Wellbeing() {
  const { data, isLoading } = useSafetyEvents();

  return (
    <PageShell
      title="Looking out for you"
      description="Moments Nova quietly noticed you might be having a hard time. It keeps these gently — only to take better care of you."
    >
      {isLoading && <div className="h-20 rounded-md bg-hairline/30" />}

      {data && data.length === 0 && (
        <p className="text-ink-soft">Nova hasn&rsquo;t had cause for concern. That&rsquo;s a good thing.</p>
      )}

      <div className="flex flex-col gap-3">
        {data?.map((e, i) => {
          const tier = TIER[e.tier] ?? { label: e.tier.replace(/_/g, " "), weight: 1 };
          return (
            <Surface key={i} className="p-5">
              <div className="flex items-center gap-2.5">
                <span className="flex gap-1" aria-hidden>
                  {[1, 2, 3].map((n) => (
                    <span
                      key={n}
                      className="h-1.5 w-1.5 rounded-full"
                      style={{ background: n <= tier.weight ? "var(--ink-soft)" : "var(--hairline)" }}
                    />
                  ))}
                </span>
                <p className="text-[15px] text-ink">{tier.label}</p>
              </div>
              <p className="mt-1.5 font-mono text-[11px] uppercase tracking-widest text-ink-faint">
                {relativeTime(e.detected_at)}
                {e.signal_types.length > 0 && ` · ${e.signal_types.join(", ")}`}
              </p>
            </Surface>
          );
        })}
      </div>

      {data && data.length > 0 && (
        <p className="mt-8 max-w-md text-sm leading-relaxed text-ink-soft">
          If you&rsquo;re carrying something heavy, you don&rsquo;t have to carry it alone — reach out
          to someone you trust, or a crisis line where you are.
        </p>
      )}
    </PageShell>
  );
}
