import { describe, expect, it, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useDictation } from "@/lib/hooks/useDictation";

describe("useDictation", () => {
  it("reports unsupported and no-ops start() when MediaRecorder is unavailable", async () => {
    const onTranscript = vi.fn();
    const { result } = renderHook(() => useDictation(onTranscript));
    expect(result.current.supported).toBe(false);
    await act(async () => {
      await result.current.start();
    });
    expect(result.current.recording).toBe(false);
    expect(onTranscript).not.toHaveBeenCalled();
  });
});
