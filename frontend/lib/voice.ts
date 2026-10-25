/*
 * Nova's voice: the keeper. Every word the app says to you comes from here or follows these rules.
 *
 *   1. Notice the specific thing. "Meera's exam is Friday" beats "You have an upcoming event".
 *   2. Dry and warm, never zany. One wry beat per screen, at most, and never where someone is hurting.
 *   3. Be honest about being unfinished: Nova is still learning you, and says so.
 *   4. Short. A margin note is a line, not a paragraph.
 *   5. Errors say what happened, that nothing is lost, and what to do. No jokes, no blame.
 *
 * Margin notes (the handwritten asides, see components/brand/Margin.tsx) are Nova thinking out loud in the
 * margin of the page. They are the one place the voice may be playful, and they are always optional reading.
 */

export type Mood =
  | "calm"
  | "thinking"
  | "happy"
  | "sleepy"
  | "startled"
  | "lost";

/** A stable pick: the same seed always gives the same line, so server and client paint agree. */
export function pick<T>(lines: readonly T[], seed: number): T {
  return lines[Math.abs(Math.trunc(seed)) % lines.length];
}

/** A number that changes once a day, so lines rotate daily without flickering on every render. */
export function daySeed(date: Date): number {
  return Math.floor(date.getTime() / 86_400_000) - date.getTimezoneOffset() / 1440;
}

type Part = "morning" | "afternoon" | "evening" | "night";

export function partOf(date: Date): Part {
  const h = date.getHours();
  if (h >= 5 && h < 12) return "morning";
  if (h >= 12 && h < 17) return "afternoon";
  if (h >= 17 && h < 22) return "evening";
  return "night";
}

const HELLO: Record<Part, { head: string; asides: string[] }> = {
  morning: {
    head: "Good morning",
    asides: [
      "kettle’s on, figuratively",
      "I’ve been keeping your place",
      "fresh page, as usual",
    ],
  },
  afternoon: {
    head: "Good afternoon",
    asides: [
      "halfway through, give or take",
      "I saved your spot",
      "tell me what the day’s been",
    ],
  },
  evening: {
    head: "Good evening",
    asides: [
      "the day is nearly a chapter",
      "sit a while",
      "I’ve got the whole evening",
    ],
  },
  night: {
    head: "Still up",
    asides: [
      "I don’t sleep, but you should, a bit",
      "quiet hours are my favourite",
      "no rush, I’m not going anywhere",
    ],
  },
};

/** Today's headline ("Good evening, Asha.") and a handwritten aside that changes by the day. */
export function hello(date: Date, name?: string | null) {
  const part = HELLO[partOf(date)];
  const who = name ? `, ${name}` : "";
  return {
    headline: `${part.head}${who}${partOf(date) === "night" ? "?" : "."}`,
    aside: pick(part.asides, daySeed(date)),
  };
}

/** While Nova writes a reply. Rotates with the message count so a long evening doesn't repeat itself. */
const THINKING = [
  "Turning that over…",
  "Finding the right words…",
  "Checking my notes…",
  "Giving that a proper think…",
  "Writing it down…",
] as const;
export const thinkingLine = (seed: number) => pick(THINKING, seed);

/** Beside a loading skeleton: what Nova is doing while you wait. */
const WAITING = [
  "Fetching that from my notes…",
  "One moment, finding the page…",
  "Dusting off the shelf…",
  "Almost there…",
] as const;
export const waitingLine = (seed: number) => pick(WAITING, seed);

/** The handwritten aside under each page's title: Nova talking about its own page. */
export const NOTES = {
  today: "Everything I’m holding for you, in one place.",
  goals: "I’ll nudge. Gently. Mostly.",
    memory: "Tear out any page you like.",
  people: "I try to spell everyone’s name right.",
  story: "One chapter a week. I’m a slow writer.",
  keepsakes: "The lines worth underlining.",
  errands: "I always ask before I touch anything.",
  care: "Not a diagnosis. Just me paying attention.",
  us: "Still getting the hang of each other.",
  upkeep: "Housekeeping. My least glamorous page.",
  privacy: "Yours. I’m only the keeper.",
  talk: "No wrong way to begin.",
} as const;
export type NoteKey = keyof typeof NOTES;

/** Empty pages: what's missing, why, and the one thing to do. Never a bare "nothing here". */
export const EMPTY = {
  goalsActive: {
    title: "Nothing in progress yet.",
    body: "Tell me what you’re working towards and it lands here, with its steps and a habit or two to help.",
    note: "a blank page is full of possibility",
  },
  goalsCompleted: {
    title: "Nothing finished yet.",
    body: "Goals you finish are kept here, so you can look back at what you’ve done.",
    note: "the good shelf",
  },
  goalsPaused: {
    title: "Nothing set aside.",
    body: "Goals you let go of rest here. There’s no shame in changing your mind.",
    note: "no judgement, ever",
  },
  keepsakesSaved: {
    title: "Nothing saved yet.",
    body: "When I say something worth keeping, hover over it in our conversation and choose “Save”. File it under any name you like.",
    note: "I’ll try to say something quotable",
  },
  keepsakesMattered: {
    title: "No moments marked yet.",
    body: "Some things you say change your life. Hover over one in our conversation and choose “This mattered”, and it’s kept here like a photograph.",
    note: "for the days that count",
  },
  errands: {
    title: "No errands yet.",
    body: "Once I do something for you, it’s listed here, so you always know what I’ve touched.",
    note: "ask me for something small",
  },
  memoryEvents: {
    title: "Nothing remembered yet.",
    body: "I don’t keep every word. I keep what seems to matter: big feelings, big news, things about your life. They appear here as we talk.",
    note: "give me something to keep",
  },
  memoryLearned: {
    title: "Nothing learned yet.",
    body: "After enough conversations I notice what stays true about you (what you like, how you work, who matters) and write it down here.",
    note: "I learn slowly, on purpose",
  },
  people: {
    title: "Nobody here yet.",
    body: "Mention your sister, a friend, a professor in passing. “Meera is visiting next week” is enough. I’ll remember them, and how things are between you.",
    note: "introduce me",
  },
  firsts: {
    title: "Everything is still ahead.",
    body: "Your first conversation, your first goal, the first moment you mark as mattering: each is kept here with the day it happened.",
    note: "firsts only happen once",
  },
  chapters: {
    title: "Your first chapter is still being written.",
    body: "I write one at the end of each week, once we’ve talked for a few days. It’s a short account of what the week was about, to come back to years from now.",
    note: "no spoilers",
  },
  care: {
    title: "Nothing to show here.",
    body: "I haven’t noticed a hard stretch. If I ever do, it will be listed here, and only you can see it.",
    note: "good news, quietly",
  },
} as const;
export type EmptyKey = keyof typeof EMPTY;

/** Errors: plain, calm, never a joke. The margin note only takes the blame. */
export const OOPS = {
  generic: "That didn’t work, and it’s on my side, not yours.",
  lost: "I can’t find that page.",
  saved: "Nothing you’ve said or saved is lost. This usually clears up on its own.",
} as const;

