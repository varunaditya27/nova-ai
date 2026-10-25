import { Section, Reveal } from "./Section";

function Exchange({ title, lines, tone }: { title: string; lines: { who: string; text: string }[]; tone: "tone" | "tone-sunk" }) {
  return (
    <div className={`${tone} flex flex-col gap-5 px-7 py-8 sm:px-9`}>
      <h3 className="font-display text-[length:var(--text-read)]">{title}</h3>
      <ul className="flex flex-col gap-4">
        {lines.map((l) => (
          <li key={l.text}>
            <span className="block text-[length:var(--text-small)] text-mute">{l.who}</span>
            <span className="read">{l.text}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

const THEM = [
  { who: "You, last month", text: "Mum’s operation is on Thursday." },
  { who: "You, today", text: "Mum’s home now." },
  { who: "A typical assistant", text: "That’s great to hear! Who is Mum, and what would you like help with?" },
];
const NOVA = [
  { who: "You, last month", text: "Mum’s operation is on Thursday." },
  { who: "You, today", text: "Mum’s home now." },
  { who: "Nova", text: "I’m so glad she’s home. How are you doing after all of Thursday?" },
];

export function Difference() {
  return (
    <Section tone="sunk" label="The difference">
      <Reveal className="mb-12 max-w-3xl">
        <h2 className="text-[length:var(--text-title)]">Most assistants start from zero every time.</h2>
        <p className="read mt-5 max-w-2xl text-ink-soft">
          You explain yourself again, and again. Nova keeps the thread, so you can pick up where you left off, whether that was yesterday or last spring.
        </p>
      </Reveal>
      <Reveal className="grid gap-6 md:grid-cols-2">
        <Exchange title="Without memory" lines={THEM} tone="tone" />
        <Exchange title="With Nova" lines={NOVA} tone="tone" />
      </Reveal>
    </Section>
  );
}
