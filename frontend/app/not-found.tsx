import { Mark } from "@/components/ui/Mark";
import { Margin } from "@/components/brand/Margin";
import { ButtonLink } from "@/components/ui/Button";
import { OOPS } from "@/lib/voice";

export default function NotFound() {
  return (
    <div className="mx-auto flex min-h-[70dvh] max-w-2xl flex-col items-start justify-center gap-5 px-6">
      <span className="flex items-end gap-4">
        <Mark size={52} mood="lost" alive quiet />
        <Margin tilt={-4} className="pb-1.5">
          I looked everywhere
        </Margin>
      </span>
      <h1 className="text-[length:var(--text-title)]">{OOPS.lost}</h1>
      <p className="read text-ink-soft">
        The page may have moved, or the link may be old. Our conversation is
        right where you left it.
      </p>
      <div className="flex flex-wrap gap-3">
        <ButtonLink href="/">Back to Talk</ButtonLink>
        <ButtonLink href="/today" variant="quiet">
          See today
        </ButtonLink>
      </div>
    </div>
  );
}
