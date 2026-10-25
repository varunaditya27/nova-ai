/** First light to last light, an hour apiece: 5 to 20. */
const HOURS = Array.from({ length: 16 }, (_, i) => i + 5);

/**
 * A ruler of the day along the foot of the page. The window's light ends on the tick for the visitor's real
 * hour (`--at`, set by the hero), marked "now": the light follows your real day, shown instead of said.
 */
export function HeroRuler() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-x-0 bottom-0 h-12">
      {HOURS.map((h) => (
        <i
          key={h}
          data-hero-tick
          className={`absolute bottom-0 w-px origin-bottom bg-ink-soft/70 ${h % 3 === 0 ? "h-7" : "h-4"}`}
          style={{ left: `${(0.03 + 0.94 * ((h - 5) / 15)) * 100}%` }}
        />
      ))}
      <i
        data-hero-now
        className="absolute bottom-0 h-11 w-[3px] origin-bottom bg-accent"
        style={{ left: "calc(var(--at, 0.5) * 100%)" }}
      />
      <span
        className="absolute bottom-12 -translate-x-1/2"
        style={{ left: "calc(var(--at, 0.5) * 100%)" }}
      >
        <span data-hero-now-label className="label block text-accent motion-safe:opacity-0">
          now
        </span>
      </span>
    </div>
  );
}
