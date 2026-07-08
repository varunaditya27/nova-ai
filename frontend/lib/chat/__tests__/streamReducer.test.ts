import { describe, expect, it } from "vitest";
import {
  initialStreamState,
  parseSSE,
  streamReducer,
  type StreamFrame,
} from "@/lib/chat/streamReducer";

describe("streamReducer", () => {
  it("meta -> tokens -> done: text is the lossless concatenation of tokens", () => {
    const frames: StreamFrame[] = [
      {
        type: "meta",
        data: {
          session_id: "s1",
          conversation_mode: "casual",
          cognitive_system: "system1",
          crisis_active: false,
          refined: false,
          confabulation_guard: false,
        },
      },
      { type: "token", data: { token: "Hey ", delay_ms: 30 } },
      { type: "token", data: { token: "there", delay_ms: 30 } },
      { type: "token", data: { token: ".", delay_ms: 30 } },
      {
        type: "done",
        data: {
          session_id: "s1",
          conversation_mode: "casual",
          cognitive_system: "system1",
          crisis_active: false,
          refined: false,
          echoes: [{ summary: "the hackathon", when: "last week", created_at: null }],
        },
      },
    ];
    const final = frames.reduce(streamReducer, initialStreamState);
    expect(final.phase).toBe("done");
    expect(final.text).toBe("Hey there.");
    expect(final.echoes).toHaveLength(1);
    expect(final.sessionId).toBe("s1");
  });

  it("an error frame moves to the error phase", () => {
    const s = streamReducer(initialStreamState, {
      type: "error",
      data: { session_id: "s1", message: "stream interrupted" },
    });
    expect(s.phase).toBe("error");
    expect(s.error).toBe("stream interrupted");
  });
});

describe("parseSSE", () => {
  it("reassembles a frame split across chunk boundaries", () => {
    const full = 'event: token\ndata: {"token":"Hi","delay_ms":40}\n\n';
    const a = full.slice(0, 20);
    const b = full.slice(20);
    const r1 = parseSSE(a, "");
    expect(r1.frames).toHaveLength(0); // incomplete → buffered
    const r2 = parseSSE(b, r1.buffer);
    expect(r2.frames).toHaveLength(1);
    expect(r2.frames[0]).toEqual({ type: "token", data: { token: "Hi", delay_ms: 40 } });
  });

  it("parses multiple frames in one chunk and leaves no buffer", () => {
    const chunk =
      'event: meta\ndata: {"session_id":"s"}\n\nevent: token\ndata: {"token":"a","delay_ms":1}\n\n';
    const { frames, buffer } = parseSSE(chunk, "");
    expect(frames.map((f) => f.type)).toEqual(["meta", "token"]);
    expect(buffer).toBe("");
  });
});
