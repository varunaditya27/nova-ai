import { Section, Reveal, SectionHead } from "./Section";
import { ScrubText } from "./ScrubText";
import { TamperChain } from "./TamperChain";

const POINTS = [
  {
    title: "It stays on your computer",
    body: "The model that talks with you runs on your own machine. Nothing you say is sent to an AI company.",
  },
  {
    title: "You can read all of it",
    body: "Everything Nova remembers about you is on the Memory page, in plain words.",
  },
  {
    title: "You can make it forget",
    body: "Ask Nova to forget something and it can never bring it up again. You get a signed receipt. The original message stays in your conversation history.",
  },
  {
    title: "Tampering shows",
    body: "Each record is sealed to the one before it. If anyone changed the past, the Privacy page would tell you.",
  },
];

export function Privacy() {
  return (
    <Section id="private" tone="ink" label="Privacy" reveal>
      <SectionHead n="07" name="Privacy" note="nobody reads over my shoulder" />
      <Reveal className="mb-14 max-w-3xl">
        <ScrubText className="text-[length:var(--text-display)] leading-[0.98]">
          What you tell Nova is yours.
        </ScrubText>
        <p className="read mt-5 max-w-2xl opacity-85">
          Someone who remembers everything about you should be someone you can
          trust completely. So Nova is built to be private, not just to say so.
        </p>
      </Reveal>
      <ul className="grid gap-x-16 gap-y-12 md:grid-cols-2">
        {POINTS.map((p) => (
          <li key={p.title}>
            <Reveal>
              <h3 className="font-display text-[length:var(--text-read)] leading-[1.15]">
                {p.title}
              </h3>
              <p className="read mt-3 max-w-md opacity-85">{p.body}</p>
            </Reveal>
          </li>
        ))}
      </ul>
      <Reveal>
        <TamperChain />
      </Reveal>
    </Section>
  );
}
