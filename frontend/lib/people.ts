import type { PersonOut } from "@/lib/api/types";

/** How things feel between you and someone, in a sentence — never a score. */
export function feeling(
  p: Pick<PersonOut, "relationship_valence" | "valence_trend">,
): string {
  const base =
    p.relationship_valence > 0.3
      ? "Things sound warm between you"
      : p.relationship_valence < -0.3
        ? "Things sound strained between you"
        : "Your feelings about them sound mixed, or simply even";
  if (p.valence_trend > 0.1) return `${base}, and getting better.`;
  if (p.valence_trend < -0.1) return `${base}, and getting harder lately.`;
  return `${base}.`;
}

const RELATIONSHIP: Record<string, string> = {
  family_immediate: "Close family",
  family_extended: "Extended family",
  romantic_partner: "Partner",
  close_friend: "Close friend",
  friend: "Friend",
  acquaintance: "Acquaintance",
  colleague: "Colleague",
  manager: "Manager",
  mentor: "Mentor",
  peer_academic: "Classmate",
  peer_professional: "Professional peer",
  authority_figure: "Someone in authority",
  rival: "Rival",
  ex: "Ex",
  online_friend: "Online friend",
  unknown: "Someone in your life",
};

/** "close_friend" → "Close friend". Anything unrecognised is tidied, never shown as a code. */
export function relationshipLabel(type: string): string {
  return RELATIONSHIP[type] ?? tidy(type);
}

const FREQUENCY: Record<string, string> = {
  daily: "You talk about them nearly every day.",
  weekly: "You mention them most weeks.",
  monthly: "You mention them now and then.",
  rarely: "They come up only rarely.",
  estranged: "You’ve mentioned them as someone you’re no longer in touch with.",
  unknown: "",
};

/** One sentence on how often they come up, or nothing when Nova can't tell yet. */
export function howOften(frequency: string): string {
  return FREQUENCY[frequency.toLowerCase()] ?? "";
}

const EVENTS: Record<string, string> = {
  conflict_onset: "An argument began",
  conflict_escalation: "An argument got worse",
  conflict_deescalation: "An argument eased",
  conflict_resolution: "An argument was settled",
  conflict_dormant: "An old argument went quiet",
  reconnection: "You got back in touch",
  deepening: "You grew closer",
  drift: "You drifted apart",
  rupture: "A break between you",
  repair: "You made things right",
  life_milestone_shared: "They shared a big moment",
  achievement_shared: "They shared an achievement",
  loss_shared: "They shared a loss",
  boundary_violation: "A boundary was crossed",
  support_received: "They supported you",
  support_withheld: "They weren’t there when you needed them",
  betrayal: "You felt betrayed",
  positive_surprise: "A pleasant surprise",
  user_set_boundary: "You set a boundary",
  user_avoided_conflict: "You steered clear of a conflict",
  user_reached_out: "You reached out",
  user_withdrew: "You pulled back",
};

export const EVENT_TYPES = Object.keys(EVENTS);

export function plainEvent(type: string): string {
  return EVENTS[type] ?? tidy(type);
}

function tidy(text: string): string {
  const spaced = text.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

export function patternSureness(confidence: number): string {
  if (confidence >= 0.8) return "Nova has seen this several times";
  if (confidence >= 0.5) return "Nova has noticed this a few times";
  return "Nova suspects this, but isn’t sure yet";
}
