"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { useIdle } from "./presence";
import type { Mood } from "@/lib/voice";

function subscribeBusy(cb: () => void) {
  const mo = new MutationObserver(cb);
  mo.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-busy"],
  });
  return () => mo.disconnect();
}

/** True while Nova is writing a reply (Talk sets `html[data-busy]`), so every stamp on screen can pulse together. */
export function useNovaBusy(): boolean {
  return useSyncExternalStore(
    subscribeBusy,
    () => document.documentElement.dataset.busy === "true",
    () => false,
  );
}

/**
 * Nova's mood for the stamp that lives in the chrome: thinking while a reply is written, asleep after a quiet
 * minute and a half, a startled jump when you come back, calm otherwise.
 */
export function useCompanionMood(sleepAfterMs = 90_000): Mood {
  const busy = useNovaBusy();
  const idle = useIdle(sleepAfterMs);
  const [startled, setStartled] = useState(false);
  const wasAsleep = useRef(false);

  useEffect(() => {
    if (idle) {
      wasAsleep.current = true;
      return;
    }
    if (!wasAsleep.current) return;
    wasAsleep.current = false;
    setStartled(true);
    const t = setTimeout(() => setStartled(false), 700);
    return () => clearTimeout(t);
  }, [idle]);

  if (busy) return "thinking";
  if (idle) return "sleepy";
  return startled ? "startled" : "calm";
}
