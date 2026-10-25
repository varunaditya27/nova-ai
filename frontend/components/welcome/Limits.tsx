import { Section, Reveal, SectionHead } from "./Section";

const ITEMS = [
  {
    title: "Not a person",
    body: "Nova is software and it can be wrong. It won’t pretend to feel things it doesn’t.",
  },
  {
    title: "Not a therapist",
    body: "It can listen and notice, but it isn’t treatment. If you’re in danger, it will point you to people who can help.",
  },
  {
    title: "Not a flatterer",
    body: "It won’t just say what you want to hear. When it disagrees, it will say so kindly.",
  },
];

export function Limits() {
  return (
    <Section label="What Nova is not">
      <SectionHead n="08" name="Limits" />
      <div className="grid gap-12 lg:grid-cols-12">
        <Reveal className="lg:sticky lg:top-32 lg:col-span-4 lg:self-start">
          <h2 className="text-[length:var(--text-title)]">What Nova is not.</h2>
        </Reveal>
        <ul className="flex flex-col gap-10 lg:col-span-7 lg:col-start-6">
          {ITEMS.map((i) => (
            <li key={i.title}>
              <Reveal>
                <h3 className="font-display text-[length:var(--text-read)] leading-[1.15]">
                  {i.title}
                </h3>
                <p className="read mt-2 max-w-xl text-ink-soft">{i.body}</p>
              </Reveal>
            </li>
          ))}
        </ul>
      </div>
    </Section>
  );
}
