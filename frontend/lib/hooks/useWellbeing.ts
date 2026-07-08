"use client";

import { useQuery } from "@tanstack/react-query";
import { getSafetyEvents } from "@/lib/api/client";

/** Layer-11 crisis-assessment log — moments Nova registered concern. */
export function useSafetyEvents() {
  return useQuery({ queryKey: ["safety"], queryFn: () => getSafetyEvents(30) });
}
