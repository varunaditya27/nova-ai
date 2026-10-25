"use client";

import { useQuery } from "@tanstack/react-query";
import { getReady } from "@/lib/api/client";

/** Nova's pulse. Polled gently; any failure simply reads as "resting" rather than an error. */
export function useAwake(): { awake: boolean; checking: boolean } {
  const q = useQuery({
    queryKey: ["ready"],
    queryFn: getReady,
    refetchInterval: 30_000,
    retry: false,
    staleTime: 0,
  });
  return { awake: q.data?.status === "ready", checking: q.isLoading };
}
