"""Voice route — Layer-9 SSML synthesis via the Kokoro TTS backend.

`POST /voice` turns a text response into speech: it builds a prosody-annotated SSML document
(per the given conversation mode) and dispatches it to Kokoro, returning the audio bytes. Voice is
best-effort — if TTS is unavailable or fails, it returns 503 so the frontend falls back to text
(matching Layer 9's degrade-to-text contract). The mode string is the same one `/chat` returns; it
is mapped to a Layer-9 prosody profile here so the client passes it through unchanged.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from api.dependencies import get_state
from api.schemas import TranscribeOut, VoiceRequest
from api.streaming import _MODE_TO_TYPING

logger = logging.getLogger("nova.api")
router = APIRouter(tags=["voice"])


@router.post("/voice")
def synthesize_voice(req: VoiceRequest, state=Depends(get_state)) -> Response:
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=422, detail="text must not be empty")
    backend = getattr(state, "voice_backend", None)
    if backend is None:
        raise HTTPException(status_code=503, detail="voice synthesis unavailable")

    from backend.layer9_output.voice_synthesizer import synthesize

    prosody_mode = _MODE_TO_TYPING.get(req.conversation_mode, req.conversation_mode)
    result = synthesize(req.text, backend, prosody_mode, apply_transforms=True, voice_id=req.voice_id)
    if not getattr(result, "ok", False):
        logger.warning("voice synthesis failed: %s", getattr(result, "error", "unknown"))
        raise HTTPException(status_code=503, detail="voice synthesis failed")
    return Response(content=result.audio_bytes,
                    media_type=getattr(result, "content_type", "audio/mpeg"))


@router.post("/voice/transcribe", response_model=TranscribeOut)
def transcribe_voice(file: UploadFile = File(...), state=Depends(get_state)):
    backend = getattr(state, "stt_backend", None)
    if backend is None:
        raise HTTPException(status_code=503, detail="speech-to-text unavailable")

    audio_bytes = file.file.read()
    result = backend.transcribe(audio_bytes, file.content_type or "audio/webm")
    if not getattr(result, "ok", False):
        logger.warning("transcription failed: %s", getattr(result, "error", "unknown"))
        raise HTTPException(status_code=503, detail="transcription failed")
    return TranscribeOut(transcript=result.transcript, confidence=result.confidence,
                         language=result.language)
