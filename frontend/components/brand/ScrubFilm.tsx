"use client";

import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";

export type ScrubHandle = { seek: (progress: number) => void };

/**
 * A film played by hand: the picture is a numbered set of frames, and where you are in the scroll chooses
 * which one is drawn. Frames load only once `active`, nearest the first frame first.
 */
export const ScrubFilm = forwardRef<
  ScrubHandle,
  {
    frames: number;
    src: (i: number) => string;
    active: boolean;
    className?: string;
  }
>(function ScrubFilm({ frames, src, active, className }, handle) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const images = useRef<(HTMLImageElement | undefined)[]>([]);
  const want = useRef(0);
  const shown = useRef(-1);

  const paint = () => {
    const c = canvas.current;
    if (!c) return;
    // draw the wanted frame, or the nearest one that has loaded
    for (let d = 0; d < frames; d++) {
      for (const i of [want.current - d, want.current + d]) {
        const img = images.current[i];
        if (img?.complete && img.naturalWidth) {
          if (shown.current === i) return;
          const ctx = c.getContext("2d")!;
          ctx.drawImage(img, 0, 0, c.width, c.height);
          shown.current = i;
          return;
        }
      }
    }
  };

  useImperativeHandle(handle, () => ({
    seek: (p) => {
      want.current = Math.max(
        0,
        Math.min(frames - 1, Math.round(p * (frames - 1))),
      );
      requestAnimationFrame(paint);
    },
  }));

  useEffect(() => {
    if (!active) return;
    let alive = true;
    const order = Array.from({ length: frames }, (_, i) => i).sort(
      (a, b) => (a % 6 === 0 ? -1 : 0) - (b % 6 === 0 ? -1 : 0),
    );
    order.forEach((i) => {
      const img = new Image();
      img.decoding = "async";
      img.onload = () => alive && paint();
      img.src = src(i);
      images.current[i] = img;
    });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `paint` and `src` are stable for a given film
  }, [active, frames]);

  return (
    <canvas
      ref={canvas}
      width={800}
      height={800}
      aria-hidden
      className={className}
    />
  );
});
