"use client";

import { useEffect } from "react";
import { NovaMark } from "@/components/primitives/NovaMark";
import { CarvedButton } from "@/components/primitives/CarvedButton";

/** The route error boundary — calm, never a raw stack trace. */
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="relative z-10 flex min-h-dvh flex-col items-center justify-center gap-6 px-6 text-center">
      <span className="text-brass">
        <NovaMark size={28} />
      </span>
      <h1
        className="font-display text-3xl text-ink"
        style={{ fontVariationSettings: '"opsz" 60, "SOFT" 30, "wght" 400' }}
      >
        Something came loose.
      </h1>
      <p className="max-w-sm text-ink-soft">
        A thread dropped somewhere. It happens — nothing was lost.
      </p>
      <CarvedButton onClick={reset}>Try again</CarvedButton>
    </main>
  );
}
