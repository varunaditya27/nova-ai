"use client";

import { Loader2, Volume2 } from "lucide-react";
import { useVoice } from "@/lib/hooks/useVoice";

/** A quiet way to hear a Nova reply. Appears on hover of a turn; silent-fails if TTS is down. */
export function VoiceButton({ text, mode = "casual" }: { text: string; mode?: string }) {
  const { speak, playing } = useVoice();
  return (
    <button
      onClick={() => speak(text, mode)}
      aria-label="Hear this reply"
      className="inline-flex items-center rounded-sm p-1 text-ink-faint opacity-0 transition-opacity duration-200 hover:text-ink-soft group-hover:opacity-100"
    >
      {playing ? <Loader2 size={13} className="animate-spin" /> : <Volume2 size={13} />}
    </button>
  );
}
