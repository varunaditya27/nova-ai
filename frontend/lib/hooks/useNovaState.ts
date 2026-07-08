"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createGoal,
  deleteGoal,
  getGoals,
  getOnboarding,
  getProactive,
  getRelationship,
  getSessions,
  updateGoal,
} from "@/lib/api/client";

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

export function useUpdateGoal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: string; patch: { status?: string; progress_score?: number } }) =>
      updateGoal(v.id, v.patch),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["goals"] }),
  });
}

export function useDeleteGoal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteGoal(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["goals"] }),
  });
}

export function useRelationship() {
  return useQuery({ queryKey: ["relationship"], queryFn: getRelationship });
}

export function useProactive() {
  return useQuery({ queryKey: ["proactive"], queryFn: () => getProactive(8) });
}

export function useOnboarding() {
  return useQuery({ queryKey: ["onboarding"], queryFn: getOnboarding });
}

export function useSessions() {
  return useQuery({ queryKey: ["sessions"], queryFn: getSessions });
}
