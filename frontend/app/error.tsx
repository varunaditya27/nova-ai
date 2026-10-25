"use client";

import { Ember } from "@/components/ui/Ember";
import { Button, ButtonLink } from "@/components/ui/Button";

/** A page failed to draw. Say so plainly, say nothing is lost, and offer both ways out. */
export default function ErrorPage({
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <div className="mx-auto flex min-h-[70dvh] max-w-2xl flex-col items-start justify-center gap-5 px-6">
      <Ember size={36} className="text-mute" />
      <h1 className="text-[length:var(--text-title)]">
        This page didn’t load properly.
      </h1>
      <p className="read text-ink-soft">
        It’s a problem on this screen, not with your conversation or anything
        Nova remembers — all of that is untouched.
      </p>
      <div className="flex flex-wrap gap-3">
        <Button onClick={reset}>Try this page again</Button>
        <ButtonLink href="/" variant="quiet">
          Go back to Talk
        </ButtonLink>
      </div>
    </div>
  );
}
