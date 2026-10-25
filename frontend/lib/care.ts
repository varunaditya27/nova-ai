import type { SafetyEvent } from "@/lib/api/types";

/** What Nova did at a logged moment of concern, said the way a friend would say it. */
export function describeCheckIn(tier: string): string {
  switch (tier) {
    case "tier_1":
      return "A very heavy moment. I set everything else aside, stayed with you, and shared where to find help right away.";
    case "tier_2":
      return "You were struggling. I checked in gently and shared ways to get support.";
    case "tier_3":
      return "You seemed to be having a hard time. I kept a gentle eye on how you were doing.";
    default:
      return "";
  }
}

/** Only the moments Nova actually acted on or watched — "none" is not an event. */
export function worthShowing(events: SafetyEvent[]): SafetyEvent[] {
  return events.filter((e) => describeCheckIn(e.tier) !== "");
}

/** Real people to call. Kept identical to the numbers Nova itself offers during a crisis. */
export const HELPLINES: {
  name: string;
  phone: string;
  tel: string;
  when: string;
}[] = [
  {
    name: "iCall",
    phone: "9152987821",
    tel: "9152987821",
    when: "Monday to Saturday, 8am–10pm",
  },
  {
    name: "Vandrevala Foundation",
    phone: "1860-2662-345",
    tel: "18602662345",
    when: "Any time, every day",
  },
  {
    name: "NIMHANS",
    phone: "080-46110007",
    tel: "08046110007",
    when: "Any time, every day",
  },
  {
    name: "Emergency services",
    phone: "112",
    tel: "112",
    when: "If you or someone is in immediate danger",
  },
];
