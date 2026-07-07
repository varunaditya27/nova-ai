import { cn } from "@/lib/cn";

/** A single 1px divider in the hairline token — the app's one border weight. */
export function Hairline({
  className,
  vertical = false,
}: {
  className?: string;
  vertical?: boolean;
}) {
  return (
    <div
      aria-hidden
      className={cn(vertical ? "w-px self-stretch" : "h-px w-full", "bg-hairline", className)}
    />
  );
}
