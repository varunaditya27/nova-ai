/**
 * The Nova mark — a point of light within an open aperture ring. Uses currentColor so callers set
 * the tone (brass for the wordmark). Decorative by default; pass a title to make it labelled.
 */
export function NovaMark({
  size = 18,
  className,
  title,
}: {
  size?: number;
  className?: string;
  title?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      className={className}
      role={title ? "img" : undefined}
      aria-hidden={title ? undefined : true}
      aria-label={title}
    >
      {title && <title>{title}</title>}
      <circle
        cx="16"
        cy="16"
        r="11"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeDasharray="60 9.3"
        transform="rotate(-96 16 16)"
      />
      <circle cx="16" cy="16" r="4.4" fill="currentColor" />
    </svg>
  );
}
