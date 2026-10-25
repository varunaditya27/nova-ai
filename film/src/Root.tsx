import { Composition } from "remotion";
import { Growth, GROWTH } from "./Growth";

export const Root = () => (
  <>
    <Composition id="Growth" component={Growth} durationInFrames={GROWTH.frames} fps={GROWTH.fps} width={GROWTH.width} height={GROWTH.height} />
  </>
);
