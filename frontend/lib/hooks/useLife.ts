"use client";

import { useQuery } from "@tanstack/react-query";
import { getCalendar, getLatestSummary, getMuseum, getSummaries } from "@/lib/api/client";

/** Weekly chapters (Layer 10 longitudinal summaries), newest first. */
export function useSummaries() {
  return useQuery({ queryKey: ["summaries"], queryFn: () => getSummaries(12) });
}

export function useLatestSummary() {
  return useQuery({ queryKey: ["summary", "latest"], queryFn: getLatestSummary });
}

export function useCalendar(start?: string, end?: string) {
  return useQuery({ queryKey: ["calendar", start, end], queryFn: () => getCalendar(start, end) });
}

export function useMuseum() {
  return useQuery({ queryKey: ["museum"], queryFn: getMuseum });
}
