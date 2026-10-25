"use client";

import { useEffect, useRef } from "react";
import { useReducedMotionSafe } from "@/lib/motion";

/**
 * The opening shot: a ten-second film that loops without a seam (source and grade in /film). It plays
 * only while it is on screen, uses a lighter file on phones, and is a still frame for anyone who
 * prefers less motion.
 */
export function HeroFilm({ className }: { className?: string }) {
  const { reduced } = useReducedMotionSafe();
  const ref = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const v = ref.current;
    if (!v || reduced) return;
    const io = new IntersectionObserver(([e]) =>
      e.isIntersecting ? v.play().catch(() => undefined) : v.pause(),
    );
    io.observe(v);
    return () => io.disconnect();
  }, [reduced]);

  if (reduced) {
    // eslint-disable-next-line @next/next/no-img-element -- a decorative still, sized by the container
    return <img src="/film/hero-poster.jpg" alt="" className={className} />;
  }
  return (
    <video
      ref={ref}
      aria-hidden
      poster="/film/hero-poster.jpg"
      autoPlay
      muted
      loop
      playsInline
      preload="auto"
      className={className}
    >
      <source
        src="/film/hero-sm.webm"
        media="(max-width: 767px)"
        type="video/webm"
      />
      <source
        src="/film/hero-sm.mp4"
        media="(max-width: 767px)"
        type="video/mp4"
      />
      <source src="/film/hero.webm" type="video/webm" />
      <source src="/film/hero.mp4" type="video/mp4" />
    </video>
  );
}
