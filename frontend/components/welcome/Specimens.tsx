import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/*
 * Still pictures of real screens, drawn with the app's own surfaces. They are decorative (the text
 * beside each one says the same thing), so they are hidden from assistive technology and contain
 * no live controls.
 */
function Frame({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div aria-hidden className={cn("tone flex flex-col gap-4 px-7 py-8 sm:px-9", className)}>
      {children}
    </div>
  );
}

const small = "text-[length:var(--text-small)] text-ink-soft";
const fakeButton = "inline-flex min-h-11 items-center rounded-full px-6 font-medium";

export function MemorySpecimen() {
  return (
    <Frame>
      <p className={small}>A memory · from three weeks ago</p>
      <p className="read">Has a Data Structures exam on Friday, and feels nervous about graphs.</p>
      <p className={small}>About: study, exams. Nova treats this as fairly important.</p>
      <span className={cn(fakeButton, "w-fit bg-sunk")}>Ask Nova to forget this</span>
    </Frame>
  );
}

export function CareSpecimen() {
  return (
    <Frame>
      <p className={small}>Nova · Tuesday evening</p>
      <p className="read">You’ve been quieter than usual this week. No need to explain. I’m here if you want to talk.</p>
      <p className={small}>If things ever feel too heavy, Nova will tell you who you can call.</p>
    </Frame>
  );
}

export function GoalSpecimen() {
  const done = [true, true, false];
  return (
    <Frame>
      <p className="read">Finish the Data Structures course</p>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-sunk">
        <div className="h-full w-2/3 rounded-full bg-accent" />
      </div>
      <ul className="flex flex-col gap-2">
        {["Arrays", "Linked lists", "Graphs"].map((m, i) => (
          <li key={m} className="flex items-center gap-3">
            <span className={cn("size-4 rounded-full", done[i] ? "bg-earned" : "bg-sunk")} />
            <span className={done[i] ? "text-ink-soft" : undefined}>{m}</span>
          </li>
        ))}
      </ul>
      <p className={small}>Habit: practise three times a week · twice so far this week</p>
    </Frame>
  );
}

export function StorySpecimen() {
  return (
    <Frame>
      <p className={small}>Chapter · the week of 3 March</p>
      <p className="font-display text-[length:var(--text-title)] leading-[1.1]">A week of nerves, and a good ending.</p>
      <p className="read text-ink-soft">
        You spent most of it dreading Friday. By Saturday the worry had turned into relief, and you were already planning what to do next.
      </p>
    </Frame>
  );
}

export function PeopleSpecimen() {
  return (
    <Frame>
      <div className="flex items-center gap-4">
        <span className="grid size-12 place-items-center rounded-full bg-accent font-display text-xl text-accent-ink">M</span>
        <div>
          <p className="read">Meera</p>
          <p className={small}>Your sister · you mention her about twice a week</p>
        </div>
      </div>
      <p className="read text-ink-soft">Last time: she’s coming to visit after your exams.</p>
    </Frame>
  );
}

export function ErrandSpecimen() {
  return (
    <Frame>
      <p className={small}>Calendar · Nova would like to</p>
      <p className="read">Add “Study group” to your calendar on Friday at 4 pm.</p>
      <p className={small}>You can undo this afterwards.</p>
      <div className="flex gap-3">
        <span className={cn(fakeButton, "bg-accent text-accent-ink")}>Go ahead</span>
        <span className={cn(fakeButton, "bg-sunk")}>Not now</span>
      </div>
    </Frame>
  );
}
