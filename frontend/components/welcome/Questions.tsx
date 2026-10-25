import { ChevronDown } from "lucide-react";
import { Section, Reveal, SectionHead } from "./Section";

const QA = [
  {
    q: "Does it need the internet?",
    a: "Not to talk. Nova’s conversation, memory and voice all run on your computer. You’ll need a connection once, to download the language model it uses.",
  },
  {
    q: "Who can see what I say?",
    a: "Anyone using your computer and signed in as you. There is no account and no sign-in, because Nova is made for one person on one computer.",
  },
  {
    q: "Is what it stores encrypted?",
    a: "Not yet. Your memories sit in a database on your own computer. Use your computer’s disk encryption if you want them locked when you’re away.",
  },
  {
    q: "Can I see what it remembers?",
    a: "Yes. The Memory page lists everything, and you can search it by meaning as well as by exact words.",
  },
  {
    q: "Can I make it forget something?",
    a: "Yes. Choose a memory, ask Nova to forget it, and confirm. It can never bring it up again, and you get a signed receipt.",
  },
  {
    q: "What if I’m in a really bad place?",
    a: "Nova will respond with care, tell you who you can call, and keep a record you can look back on. It isn’t a substitute for those people.",
  },
  {
    q: "Which AI is it using?",
    a: "An open language model that runs on your computer. Which one is up to you, and you can change it later.",
  },
];

export function Questions() {
  return (
    <Section id="questions" tone="sunk" label="Questions">
      <SectionHead n="09" name="Questions" note="ask away" />
      <div className="grid gap-12 lg:grid-cols-12">
        <Reveal className="lg:sticky lg:top-32 lg:col-span-4 lg:self-start">
          <h2 className="text-[length:var(--text-title)]">
            Questions people ask.
          </h2>
        </Reveal>
        <Reveal className="lg:col-span-7 lg:col-start-6">
          <ul className="flex flex-col gap-3">
            {QA.map((item) => (
              <li key={item.q}>
                <details className="tone group px-6">
                  <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-4 py-3 font-display text-[length:var(--text-read)] [&::-webkit-details-marker]:hidden">
                    {item.q}
                    <ChevronDown
                      aria-hidden
                      size={20}
                      className="shrink-0 transition-transform duration-200 group-open:rotate-180"
                    />
                  </summary>
                  <p className="read pb-6 pr-8 text-ink-soft">{item.a}</p>
                </details>
              </li>
            ))}
          </ul>
        </Reveal>
      </div>
    </Section>
  );
}
