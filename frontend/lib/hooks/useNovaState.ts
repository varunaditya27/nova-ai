"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createGoal, getGoals, getProactive, getRelationship } from "@/lib/api/client";

export function useGoals(status?: string) {
  return useQuery({ queryKey: ["goals", status ?? "active"], queryFn: () => getGoals(status) });
}

export function useCreateGoal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { title: string; description?: string }) =>
      createGoal(vars.title, vars.description),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["goals"] }),
  });
}

export function useRelationship() {
  return useQuery({ queryKey: ["relationship"], queryFn: getRelationship });
}

export function useProactive() {
  return useQuery({ queryKey: ["proactive"], queryFn: () => getProactive(8) });
}
