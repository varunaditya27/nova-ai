/**
 * The relationship stages, in plain words. `meaning` mirrors what Nova's behaviour actually changes
 * at each stage (backend: layer4 relationship_manager) — it is a description, not decoration.
 * `upTo` is the last session count that still belongs to the stage.
 */
export type Stage = {
  id: string;
  name: string;
  upTo: number | null;
  meaning: string;
};

export const STAGES: Stage[] = [
  {
    id: "new",
    name: "Just meeting",
    upTo: 3,
    meaning: "Nova keeps things light and doesn’t bring up past conversations yet — it’s still learning who you are.",
  },
  {
    id: "acquaintance",
    name: "Getting comfortable",
    upTo: 15,
    meaning: "Nova may gently mention things you’ve told it before, and asks a few more questions.",
  },
  {
    id: "developing",
    name: "Building trust",
    upTo: 40,
    meaning: "Nova refers back to earlier conversations naturally and follows up on what matters to you.",
  },
  {
    id: "established",
    name: "Old friends",
    upTo: 100,
    meaning: "Nova draws freely on your shared history, and can tell you when something seems off.",
  },
  {
    id: "close",
    name: "Close",
    upTo: null,
    meaning: "Nova is fully at ease with you. It can say hard things kindly, and it remembers across years.",
  },
];

export function stageById(id: string): Stage {
  return STAGES.find((s) => s.id === id) ?? STAGES[0];
}

/** How many more conversations until the next stage, or null at the last. */
export function toNextStage(stageId: string, sessions: number): { next: Stage; remaining: number } | null {
  const i = STAGES.findIndex((s) => s.id === stageId);
  const current = STAGES[i];
  if (!current || current.upTo === null) return null;
  return { next: STAGES[i + 1], remaining: Math.max(1, current.upTo + 1 - sessions) };
}
