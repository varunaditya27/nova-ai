"use client";

import { MotionConfig } from "motion/react";
import { Capabilities } from "@/components/welcome/Capabilities";
import { Closing } from "@/components/welcome/Closing";
import { Difference } from "@/components/welcome/Difference";
import { Growth } from "@/components/welcome/Growth";
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
      <Header />
      <Hero />
      <Difference />
      <Growth />
      <Capabilities />
      <LightDemo />
      <Privacy />
      <Limits />
      <Questions />
      <Closing />
    </MotionConfig>
  );
}
