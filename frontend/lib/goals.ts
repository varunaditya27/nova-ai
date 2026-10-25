const STATUS: Record<string, string> = {
  active: "In progress",
  on_track: "On track",
  at_risk: "Slipping — could use some attention",
  tentative: "Still taking shape",
  completed: "Done",
  abandoned: "Set aside",
  paused: "Paused",
};

export function statusWords(status: string): string {
  return STATUS[status] ?? status.replace(/_/g, " ");
}

export const isFinished = (status: string) => status === "completed";

const EVERY: Record<string, string> = {
  daily: "every day",
  weekly: "every week",
  weekdays: "on weekdays",
  custom: "on your own schedule",
};

export function habitCadence(frequency: string): string {
  return EVERY[frequency] ?? frequency.replace(/_/g, " ");
}

/** "5 days in a row" / "3 weeks in a row" — streaks count in the habit's own unit. */
export function streakWords(streak: number, frequency: string): string {
  if (streak <= 0) return "Not started — tell Nova when you do it";
  const unit = frequency === "weekly" ? "week" : "day";
  return `${streak} ${unit}${streak === 1 ? "" : "s"} in a row`;
}
