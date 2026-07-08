"use client";

import { useQuery } from "@tanstack/react-query";
import { getHome } from "@/lib/api/client";

/** The Digital Desk aggregation (GET /home). */
export function useHome() {
  return useQuery({ queryKey: ["home"], queryFn: getHome });
}
