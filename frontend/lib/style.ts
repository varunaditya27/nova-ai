import type { RelationshipOut } from "@/lib/api/types";

export type Spectrum = {
  key: string;
  left: string;
  right: string;
  /** 0..1 position on the track. */
  at: number;
  /** A plain sentence about what Nova does with it. */
  sentence: string;
};

const clamp = (n: number) => Math.max(0, Math.min(1, n));

/** The four things Nova has learned about how you like to talk, each as a spectrum plus a sentence. */
export function spectrums(
  r: Pick<
    RelationshipOut,
    | "formality_preference"
    | "response_length_preference"
    | "question_tolerance"
    | "unsolicited_advice_tolerance"
  >,
): Spectrum[] {
  const f = clamp(r.formality_preference);
  const l = clamp(r.response_length_preference);
  const q = clamp(r.question_tolerance);
  const a = clamp(r.unsolicited_advice_tolerance);
  return [
    {
      key: "formality",
      left: "Casual",
      right: "Formal",
      at: f,
      sentence:
        f < 0.4
          ? "You write casually, so Nova keeps it relaxed."
          : f > 0.6
            ? "You write formally, so Nova keeps it measured."
            : "Nova matches your in-between tone.",
    },
    {
      key: "length",
      left: "Short replies",
      right: "Detailed replies",
      at: l,
      sentence:
        l < 0.4
          ? "You like it brief, so Nova gets to the point."
          : l > 0.6
            ? "You like depth, so Nova explains fully."
            : "Nova gives replies of a middling length.",
    },
    {
      key: "questions",
      left: "Fewer questions",
      right: "Enjoys being asked",
      at: q,
      sentence:
        q < 0.4
          ? "Nova asks you fewer questions."
          : q > 0.6
            ? "You seem to enjoy being asked, so Nova asks more."
            : "Nova asks a moderate number of questions.",
    },
    {
      key: "advice",
      left: "Just listen",
      right: "Welcomes advice",
      at: a,
      sentence:
        a < 0.4
          ? "Nova holds back advice unless you ask for it."
          : a > 0.6
            ? "You welcome advice, so Nova offers it freely."
            : "Nova offers advice now and then.",
    },
  ];
}

/** A score in [0,1] as a few honest words. */
export function closeness(n: number): string {
  if (n < 0.2) return "Still early";
  if (n < 0.5) return "Growing";
  if (n < 0.75) return "Close";
  return "Very close";
}
