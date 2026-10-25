"use client";

import { useEffect, useSyncExternalStore } from "react";

/*
 * One shared listener for everything that watches you: where the pointer is (so the stamp can lean toward it)
 * and how long it has been since you did anything (so Nova can doze off, and startle awake).
 */
const pointer = { x: -1, y: -1, moved: 0 };
let lastActive = 0;
const watchers = new Set<() => void>();
let attached = false;

function attach() {
  if (attached || typeof window === "undefined") return;
  attached = true;
  lastActive = Date.now();
  let frame = 0;
  const wake = () => {
    lastActive = Date.now();
  };
  window.addEventListener(
    "pointermove",
    (e) => {
      pointer.x = e.clientX;
      pointer.y = e.clientY;
      pointer.moved++;
      wake();
      if (!frame)
        frame = requestAnimationFrame(() => {
          frame = 0;
          watchers.forEach((w) => w());
        });
    },
    { passive: true },
  );
  for (const ev of ["keydown", "pointerdown", "scroll", "touchstart"])
    window.addEventListener(ev, wake, { passive: true, capture: true });
}

/** Calls `fn` (at most once a frame) whenever the pointer moves; returns the live position. */
export function useWatchPointer(
  enabled: boolean,
  fn: (p: { x: number; y: number }) => void,
) {
  useEffect(() => {
    if (!enabled) return;
    attach();
    const cb = () => fn(pointer);
    watchers.add(cb);
    return () => void watchers.delete(cb);
  }, [enabled, fn]);
}

const tick = new Set<() => void>();
let timer: ReturnType<typeof setInterval> | undefined;
function subscribeTick(cb: () => void) {
  attach();
  tick.add(cb);
  timer ??= setInterval(() => tick.forEach((t) => t()), 5000);
  return () => {
    tick.delete(cb);
    if (!tick.size && timer) {
      clearInterval(timer);
      timer = undefined;
    }
  };
}

/** True once you have done nothing for `ms`. Flips back the moment you move, type or scroll. */
export function useIdle(ms: number): boolean {
  return useSyncExternalStore(
    subscribeTick,
    () => Date.now() - lastActive > ms,
    () => false,
  );
}
