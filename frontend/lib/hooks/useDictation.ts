"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { transcribeVoice } from "@/lib/api/client";

/** Push-to-talk dictation: hold to record, release to transcribe. Progressive enhancement —
 * `supported` is false (and start/stop are no-ops) when the browser lacks MediaRecorder or the
 * user denies mic permission, so callers can hide the control entirely rather than show a broken
 * one. Starts false and flips in an effect (never computed inline during render) so the
 * server-rendered HTML and the first client render always agree — computing it inline caused a
 * real hydration mismatch (server has no `window`, client does). */
export function useDictation(onTranscript: (text: string) => void) {
  const [supported, setSupported] = useState(false);
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  // Feature detection can only run client-side; this is the standard isomorphic pattern (start
  // false, flip after mount) so SSR and the first client render always agree.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSupported("mediaDevices" in navigator && typeof MediaRecorder !== "undefined");
  }, []);

  const start = useCallback(async () => {
    if (!supported || recording) return;
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = async () => {
        streamRef.current?.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        setTranscribing(true);
        try {
          const result = await transcribeVoice(blob);
          if (result.transcript) onTranscript(result.transcript);
        } catch {
          setError("Couldn't transcribe that.");
        } finally {
          setTranscribing(false);
        }
      };
      recorderRef.current = recorder;
      recorder.start();
      setRecording(true);
    } catch {
      setError("Microphone unavailable.");
    }
  }, [supported, recording, onTranscript]);

  const stop = useCallback(() => {
    if (!recording) return;
    recorderRef.current?.stop();
    setRecording(false);
  }, [recording]);

  return { supported, recording, transcribing, error, start, stop };
}
