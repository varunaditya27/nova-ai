"use client";

import { MotionConfig } from "motion/react";
import { Capabilities } from "@/components/welcome/Capabilities";
import { Closing } from "@/components/welcome/Closing";
import { Constellation } from "@/components/welcome/Constellation";
import { Difference } from "@/components/welcome/Difference";
import { Growth } from "@/components/welcome/Growth";
import { ThreadProof } from "@/components/welcome/ThreadProof";
import { ChapterRail } from "@/components/welcome/ChapterRail";
import { Cursor } from "@/components/welcome/Cursor";
import { Intro } from "@/components/welcome/Intro";
import { Marquee } from "@/components/welcome/Marquee";
import { SmoothScroll } from "@/components/welcome/SmoothScroll";
import { Header } from "@/components/welcome/Header";
import { Hero } from "@/components/welcome/Hero";
import { LightDemo } from "@/components/welcome/LightDemo";
import { Limits } from "@/components/welcome/Limits";
import { Privacy } from "@/components/welcome/Privacy";
import { Questions } from "@/components/welcome/Questions";

/** The front door: what Nova is, how it grows, what it does, what it won't, and how it protects you. */
export default function Welcome() {
  return (
    <MotionConfig reducedMotion="user">
      <div className="grain">
        <SmoothScroll />
        <Header />
        <Hero />
        <Marquee />
        <ThreadProof />
        <Difference />
        <Growth />
        <Constellation />
        <Capabilities />
        <LightDemo />
        <Privacy />
        <Limits />
        <Questions />
        <Closing />
        <ChapterRail />
        <Cursor />
        <Intro />
      </div>
    </MotionConfig>
  );
}
