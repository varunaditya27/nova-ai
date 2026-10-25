import "@fontsource/libre-baskerville/latin-700-italic.css";
import { useEffect, useState } from "react";
import { continueRender, delayRender } from "remotion";

/** Wait for the brand face before drawing a frame, so the "n" is never a fallback letter. */
export function useBrandFont(): void {
  const [handle] = useState(() => delayRender("Libre Baskerville"));
  useEffect(() => {
    document.fonts.load("italic 700 40px 'Libre Baskerville'").then(() => continueRender(handle));
  }, [handle]);
}

/** Nova's bookplate: a maroon square with its corner folded over and a single italic "n". Same geometry as the web app's `Mark`. */
export function Stamp({ size, glow = 1 }: { size: number; glow?: number }) {
  const c = size * 0.3;
  return (
    <div style={{ position: "relative", width: size, height: size, filter: `drop-shadow(0 0 ${size * 0.35}px rgba(248,113,113,${0.55 * glow}))` }}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: "#9b1c1c",
          clipPath: `polygon(0 0, calc(100% - ${c}px) 0, 100% ${c}px, 100% 100%, 0 100%)`,
          display: "grid",
          placeItems: "center",
          color: "#fff",
          fontFamily: "'Libre Baskerville', Georgia, serif",
          fontStyle: "italic",
          fontWeight: 700,
          fontSize: size * 0.7,
          lineHeight: 1,
        }}
      >
        <span style={{ transform: `translateY(${-size * 0.03}px)` }}>n</span>
      </div>
      <div style={{ position: "absolute", top: 0, right: 0, width: c, height: c, background: "linear-gradient(to bottom left, transparent 50%, rgba(0,0,0,0.32) 50%)" }} />
    </div>
  );
}
