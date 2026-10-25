"use client";

import { useCallback, useSyncExternalStore } from "react";

const KEY = "nova-cursor";
const EVENT = "nova-cursor-preference";

function read(): boolean {
  try {
    return localStorage.getItem(KEY) !== "off";
  } catch {
    return true;
  }
}

function subscribe(cb: () => void): () => void {
  window.addEventListener(EVENT, cb);
  window.addEventListener("storage", cb);
  return () => {
    window.removeEventListener(EVENT, cb);
    window.removeEventListener("storage", cb);
  };
}

/** Whether Nova's own cursor is on. It is by default; anyone can switch it off and get their system cursor back. */
export function useCursorPreference(): [boolean, (on: boolean) => void] {
  const on = useSyncExternalStore(subscribe, read, () => true);
  const set = useCallback((next: boolean) => {
    try {
      localStorage.setItem(KEY, next ? "on" : "off");
    } catch {
      /* private mode: the choice lasts until reload */
    }
    window.dispatchEvent(new Event(EVENT));
  }, []);
  return [on, set];
}
