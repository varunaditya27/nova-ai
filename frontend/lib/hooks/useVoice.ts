"use client";

import { useCallback, useRef, useState } from "react";
import { postVoice } from "@/lib/api/client";

/**
 * Speak a Nova reply via Kokoro TTS. On any failure (503 when TTS is down) it stays silent — the
 * reply is already on screen as text, so voice is purely additive and never blocks.
 */
export function useVoice() {
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const speak = useCallback(async (text: string, mode = "casual") => {
    try {
      const blob = await postVoice(text, mode);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;
      setPlaying(true);
      audio.onended = () => {
        setPlaying(false);
        URL.revokeObjectURL(url);
      };
      await audio.play();
    } catch {
      setPlaying(false); // voice unavailable — quietly remain text
    }
  }, []);

  const stop = useCallback(() => {
    audioRef.current?.pause();
    setPlaying(false);
  }, []);

  return { speak, stop, playing };
}
