/**
 * The page and the light on it, behind the type. Three layers: a shade that lifts as the day arrives, a
 * window's light with its mullions that heroScore slides across the page, and a soft vignette. The stage
 * and push wrappers are the two camera moves (the opening's dolly, then the scroll's).
 */
export function HeroLight() {
  return (
    <div data-hero-stage aria-hidden className="pointer-events-none absolute inset-0 -z-10">
      <div data-hero-push className="absolute inset-0">
        <div
          data-hero-beam
          className="absolute -top-[10%] left-0 h-[120%] w-[56%] text-[#fff0cf] opacity-50"
        >
          <svg
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            fill="currentColor"
            className="size-full blur-[10px]"
          >
            {[0, 52].flatMap((x) =>
              [0, 34.67, 69.33].map((y) => (
                <rect key={`${x}-${y}`} x={x} y={y} width="48" height="30.67" />
              )),
            )}
          </svg>
        </div>
        <div data-hero-shade className="absolute inset-0 bg-[#140c08] opacity-0 mix-blend-multiply motion-safe:opacity-75" />
        <div
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(ellipse 80% 70% at 60% 45%, transparent 55%, rgb(20 12 8 / 0.06))",
          }}
        />
      </div>
    </div>
  );
}
