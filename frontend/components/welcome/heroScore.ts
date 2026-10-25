import { gsap } from "@/lib/gsap";
import type { DayLight } from "@/lib/welcome/dayLight";

/** The window's light is this wide, as a share of the page. */
const BEAM = 0.56;
/** Where the shade settles once the light has arrived. Keep in step with HeroLight's `opacity-0`. */
export const SHADE_END = 0;

/** The beam's offset, in its own widths, that centres it at `at` (a share of the page width). */
export const beamX = (at: number) => (at / BEAM - 0.5) * 100;

/** When the stamp touches the page. Every reaction starts on this frame, not shortly after. */
const HIT = 2.39;

/**
 * The opening, about 3.4 s. The day's light crosses the page and lands on the real hour while the camera
 * eases in; the headline is set line by line; one ink stroke; a held beat; then the stamp lands and
 * everything it touches reacts in the same frame, and the rest of the page arrives behind it.
 * Direction of travel is up and to the right (toward the folded corner) throughout.
 */
export function openingScore(root: HTMLElement, dawn: DayLight, now: DayLight) {
  const q = gsap.utils.selector(root);
  const beam = q("[data-hero-beam]");
  const copy = q("[data-hero-copy]");
  return gsap
    .timeline({ delay: 0.1 })
    .fromTo(
      q("[data-hero-stage]"),
      { scale: 1.06, xPercent: -1.2, yPercent: 1.2 },
      { scale: 1, xPercent: 0, yPercent: 0, duration: 3.4, ease: "power2.out" },
      0,
    )
    .fromTo(
      beam,
      { xPercent: beamX(dawn.at), skewX: dawn.skew, opacity: 0, color: dawn.tint },
      { xPercent: beamX(now.at), skewX: now.skew, opacity: now.strength, color: now.tint, duration: 1.4, ease: "power2.inOut" },
      0,
    )
    .fromTo(q("[data-hero-shade]"), { opacity: 0.75 }, { opacity: SHADE_END, duration: 1.4, ease: "power2.inOut" }, 0)
    .fromTo(
      q("[data-hero-line]"),
      { yPercent: 110, autoAlpha: 0, filter: "blur(6px)" },
      { yPercent: 0, autoAlpha: 1, filter: "blur(0px)", duration: 0.8, stagger: 0.12, ease: "power4.out" },
      0.35,
    )
    .fromTo(q("[data-hero-ink-line]"), { drawSVG: "0%" }, { drawSVG: "100%", duration: 0.5, ease: "power2.out" }, 1.25)
    .fromTo(
      q("[data-hero-stamp]"),
      { autoAlpha: 0, scale: 1.5, y: -30, filter: "blur(6px)" },
      { autoAlpha: 1, scale: 1, y: 0, filter: "blur(0px)", duration: 0.34, ease: "power4.in" },
      HIT - 0.34,
    )
    .fromTo(q("[data-hero-shadow]"), { scale: 1.6, autoAlpha: 0.1 }, { scale: 1, autoAlpha: 0.5, duration: 0.34, ease: "power4.in" }, HIT - 0.34)
    .fromTo(q("[data-hero-ink]"), { scale: 0.5, autoAlpha: 0.9 }, { scale: 1, autoAlpha: 0, duration: 0.7, ease: "power2.out" }, HIT)
    .to(copy, { y: 3, scale: 0.997, transformOrigin: "left bottom", duration: 0.09, ease: "power1.out" }, HIT)
    .to(copy, { y: 0, scale: 1, duration: 0.4, ease: "power2.out" }, HIT + 0.09)
    .to(beam, { opacity: Math.min(1, now.strength + 0.12), duration: 0.06 }, HIT)
    .to(beam, { opacity: now.strength, duration: 0.4, ease: "power2.out" }, HIT + 0.06)
    .fromTo(
      q("[data-hero-item]"),
      { autoAlpha: 0, y: 24, filter: "blur(8px)" },
      { autoAlpha: 1, y: 0, filter: "blur(0px)", duration: 0.8, stagger: 0.1, ease: "power4.out" },
      HIT + 0.06,
    )
    .fromTo(q("[data-hero-tick]"), { scaleY: 0 }, { scaleY: 1, duration: 0.4, stagger: 0.03, ease: "power3.out" }, HIT + 0.1)
    .fromTo(q("[data-hero-now]"), { scaleY: 0 }, { scaleY: 1, duration: 0.5, ease: "power3.out" }, HIT + 0.65)
    .fromTo(q("[data-hero-now-label]"), { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.4, ease: "power2.out" }, HIT + 0.9);
}

/** The scene keeps moving as you leave it: the camera pushes on, the light travels toward dusk, the copy lifts away. */
export function scrollScore(root: HTMLElement, now: DayLight) {
  const q = gsap.utils.selector(root);
  const scrub = { trigger: root, start: "top top", end: "bottom top", scrub: true };
  gsap.to(q("[data-hero-push]"), { scale: 1.12, ease: "none", scrollTrigger: scrub });
  gsap.fromTo(
    q("[data-hero-beam]"),
    { xPercent: beamX(now.at), skewX: now.skew },
    { xPercent: beamX(Math.min(0.97, now.at + 0.25)), skewX: now.skew - 12, ease: "none", immediateRender: false, scrollTrigger: scrub },
  );
  gsap.to(q("[data-hero-copy]"), {
    yPercent: -12,
    autoAlpha: 0.15,
    ease: "none",
    scrollTrigger: { ...scrub, end: "bottom 30%" },
  });
}

/**
 * The page lifts as you leave it: the bottom-right corner curls up and to the left (`--p` is the size of the
 * lift; the clip and the flap in Hero read it). The top-right dog-ear stays put as the mark; the bottom edge is
 * the one in view while the hero scrolls away, so that is where the turn is visible.
 */
export function pagePeel(root: HTMLElement) {
  const h = window.innerHeight;
  gsap.fromTo(
    root,
    { "--p": "0px" },
    {
      "--p": `${Math.min(root.clientWidth * 0.36, h * 0.6)}px`,
      ease: "power1.inOut",
      immediateRender: false,
      scrollTrigger: { trigger: root, start: "top top", end: `+=${h * 0.5}`, scrub: true },
    },
  );
}
