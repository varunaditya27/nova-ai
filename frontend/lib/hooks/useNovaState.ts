"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createGoal,
  deleteGoal,
  getGoal,
  getGoals,
  getOnboarding,
  getProactive,
  getRelationship,
  getSessions,
  updateGoal,
} from "@/lib/api/client";

export function useGoals(status?: string) {
  return useQuery({
    queryKey: ["goals", status ?? "active"],
    queryFn: () => getGoals(status),
  });
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
    mutationFn: (v: {
      id: string;
      patch: { status?: string; progress_score?: number };
    }) => updateGoal(v.id, v.patch),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["goals"] });
      qc.invalidateQueries({ queryKey: ["goal"] });
      qc.invalidateQueries({ queryKey: ["home"] });
    },
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

export function useGoal(id: string) {
  return useQuery({
    queryKey: ["goal", id],
    queryFn: () => getGoal(id),
    enabled: Boolean(id),
  });
}
