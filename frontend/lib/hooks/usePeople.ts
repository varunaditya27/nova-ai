"use client";

import { useQuery } from "@tanstack/react-query";
import { getPeople, getPerson } from "@/lib/api/client";

export function usePeople() {
  return useQuery({ queryKey: ["people"], queryFn: getPeople });
}

export function usePerson(personId: string) {
  return useQuery({
    queryKey: ["people", personId],
    queryFn: () => getPerson(personId),
    enabled: Boolean(personId),
  });
}
