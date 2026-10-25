"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  confirmTool,
  denyTool,
  getPendingTools,
  getToolHistory,
  undoTool,
} from "@/lib/api/client";

/** Pending SOFT/HARD confirmations. Polled, since there is no push channel. */
export function usePendingTools() {
  return useQuery({
    queryKey: ["tools", "pending"],
    queryFn: getPendingTools,
    refetchInterval: 8000,
  });
}

export function useToolHistory() {
  return useQuery({ queryKey: ["tools", "history"], queryFn: getToolHistory });
}

/** Confirm (execute) or deny a pending action; both refresh the pending list + history. */
export function useToolActions() {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: ["tools"] });
  const confirm = useMutation({
    mutationFn: confirmTool,
    onSuccess: invalidate,
  });
  const deny = useMutation({ mutationFn: denyTool, onSuccess: invalidate });
  const undo = useMutation({ mutationFn: undoTool, onSuccess: invalidate });
  return { confirm, deny, undo };
}
