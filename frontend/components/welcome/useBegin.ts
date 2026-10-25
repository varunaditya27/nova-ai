"use client";

import { useRouter } from "next/navigation";

/** Mark the front door as seen, then go to the conversation. */
export function useBegin() {
  const router = useRouter();
  return () => {
    try {
      localStorage.setItem("nova-welcomed", "1");
    } catch {
      /* private mode: still let them in */
    }
    router.push("/");
  };
}
