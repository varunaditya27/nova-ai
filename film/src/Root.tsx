import { Composition } from "remotion";
import { Hero, HERO } from "./Hero";

export const Root = () => (
  <Composition id="Hero" component={Hero} durationInFrames={HERO.frames} fps={HERO.fps} width={HERO.width} height={HERO.height} />
);
