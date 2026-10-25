import { Mark } from "@/components/ui/Mark";
import { ButtonLink } from "@/components/ui/Button";

export default function NotFound() {
  return (
    <div className="mx-auto flex min-h-[70dvh] max-w-2xl flex-col items-start justify-center gap-5 px-6">
      <Mark size={44} quiet />
      <h1 className="text-[length:var(--text-title)]">
        There’s nothing at this address.
      </h1>
      <p className="read text-ink-soft">
        The page may have moved, or the link may be old. Your conversation is
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
