/** Tiny class- name joiner — drops falsy values. Avoids pulling in clsx for this small need. */
export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}
