"use client";

import { useState } from "react";
import { Page } from "@/components/ui/Page";
import { Tabs } from "@/components/ui/Tabs";
import { Chapters } from "@/components/story/Chapters";
import { Days } from "@/components/story/Days";
import { Firsts } from "@/components/story/Firsts";

type Tab = "chapters" | "days" | "firsts";

/** Our story: the same relationship, read three ways — by week, by day, and by its firsts. */
export default function Story() {
  const [tab, setTab] = useState<Tab>("chapters");
  return (
    <Page
      title="Our story"
      intro="Nova writes a chapter for each week. Days shows when you talked, and Firsts keeps the things that happened for the first time."
      actions={
        <Tabs
          label="How to read our story"
          value={tab}
          onChange={setTab}
          items={[
            { value: "chapters", label: "Chapters" },
            { value: "days", label: "Days" },
            { value: "firsts", label: "Firsts" },
          ]}
        />
      }
    >
      {tab === "chapters" && <Chapters />}
      {tab === "days" && <Days />}
      {tab === "firsts" && <Firsts />}
    </Page>
  );
}
