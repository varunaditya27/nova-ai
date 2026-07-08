"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  deleteMemory,
  getBookmarks,
  getIntegrity,
  getMemoryAudit,
  getMilestones,
  getSyncStatus,
  removeBookmark,
  removeMilestone,
  setBookmark,
  setMilestone,
} from "@/lib/api/client";

export function useMemoryAudit() {
  return useQuery({ queryKey: ["memory-audit"], queryFn: getMemoryAudit });
}

export function useIntegrity() {
  return useQuery({ queryKey: ["integrity"], queryFn: getIntegrity });
}

export function useSyncStatus() {
  return useQuery({ queryKey: ["sync-status"], queryFn: getSyncStatus });
}

export function useDeleteMemory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (memoryId: string) => deleteMemory(memoryId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["memory-audit"] });
      qc.invalidateQueries({ queryKey: ["integrity"] });
    },
  });
}

export function useBookmarks(category?: string) {
  return useQuery({
    queryKey: ["bookmarks", category ?? "all"],
    queryFn: () => getBookmarks(category),
  });
}

export function useMilestones() {
  return useQuery({ queryKey: ["milestones"], queryFn: getMilestones });
}

/** Toggle a message's bookmark/milestone flag; refreshes the thread + the relevant lens list. */
export function useAnnotate() {
  const qc = useQueryClient();
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["messages"] });
    qc.invalidateQueries({ queryKey: ["bookmarks"] });
    qc.invalidateQueries({ queryKey: ["milestones"] });
  };
  const bookmark = useMutation({
    mutationFn: (v: { id: string; on: boolean; category?: string }) =>
      v.on ? setBookmark(v.id, v.category) : removeBookmark(v.id),
    onSuccess: invalidate,
  });
  const milestone = useMutation({
    mutationFn: (v: { id: string; on: boolean; label?: string }) =>
      v.on ? setMilestone(v.id, v.label) : removeMilestone(v.id),
    onSuccess: invalidate,
  });
  return { bookmark, milestone };
}
