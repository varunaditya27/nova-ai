import { Composition } from "remotion";
import { Growth, GROWTH } from "./Growth";
import { Hero, HERO } from "./Hero";

export const Root = () => (
  <>
    <Composition id="Hero" component={Hero} durationInFrames={HERO.frames} fps={HERO.fps} width={HERO.width} height={HERO.height} />
    <Composition id="Growth" component={Growth} durationInFrames={GROWTH.frames} fps={GROWTH.fps} width={GROWTH.width} height={GROWTH.height} />
  </>
);
