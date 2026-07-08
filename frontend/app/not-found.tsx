import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { NovaMark } from "@/components/primitives/NovaMark";

/** A warm 404 — honest about the emptiness rather than shouting an error. */
export default function NotFound() {
  return (
    <main className="relative z-10 flex min-h-dvh flex-col items-center justify-center gap-6 px-6 text-center">
      <span className="text-brass">
        <NovaMark size={28} />
      </span>
      <h1
        className="font-display text-3xl text-ink"
        style={{ fontVariationSettings: '"opsz" 60, "SOFT" 30, "wght" 400' }}
      >
        This page hasn&rsquo;t been written yet.
      </h1>
      <p className="max-w-sm text-ink-soft">
        There&rsquo;s nothing here — which, for a page, is a kind of honesty.
      </p>
      <Link
        href="/desk"
        style={{ boxShadow: "inset 0 1px 0 var(--wake)" }}
        className="group inline-flex items-center gap-2 rounded-md border border-hairline bg-surface px-5 py-2.5 text-sm font-medium text-ink transition-colors hover:bg-raised"
      >
        Back to the desk
        <ArrowRight size={15} className="transition-transform duration-300 group-hover:translate-x-0.5" />
      </Link>
    </main>
  );
}
