"""Gemini Live Audio Chat node — real one-shot Live API session.

This is intentionally synchronous from ComfyUI's point of view: each node run
opens a Live API WebSocket session, sends the provided text/audio, collects the
model's audio/text response until turn completion, and closes the session.
"""
from __future__ import annotations

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor

import torch

from .gemini_common import (
    HAS_GENAI,
    LIVE_MODELS,
    audio_dict_to_pcm16,
    build_client,
    get_api_key,
    is_model_unavailable,
    is_transient,
    pcm16_to_audio,
)


class GeminiAudioChat:
    LIVE_MODELS = LIVE_MODELS

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text_input": ("STRING", {"multiline": True, "default": "Hello! How are you?"}),
                "system_prompt": ("STRING", {"multiline": True, "default": "You are a helpful voice assistant."}),
                "model": (cls.LIVE_MODELS, {"default": "gemini-3.8-live"}),
            },
            "optional": {
                "audio_input": ("AUDIO",),
                "voice": (["Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede", "Callirhoe"], {"default": "Kore"}),
                "api_key": ("STRING", {"default": ""}),
                "proxy": ("STRING", {"default": ""}),
                "fallback_enabled": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("AUDIO", "STRING", "STRING")
    RETURN_NAMES = ("audio_output", "text_response", "session_info")
    FUNCTION = "chat"
    CATEGORY = "Gemini 3.x"

    @staticmethod
    async def _run_session(client, model, text_input, system_prompt, audio_input, voice):
        config = {
            "response_modalities": ["AUDIO"],
            "output_audio_transcription": {},
        }
        if system_prompt.strip():
            config["system_instruction"] = system_prompt.strip()
        # Voice selection is supported by Live native-audio models; keep the field
        # in the config dict so SDK versions that support it can pass it through.
        config["speech_config"] = {
            "voice_config": {
                "prebuilt_voice_config": {"voice_name": voice}
            }
        }

        audio_chunks: list[bytes] = []
        transcript_chunks: list[str] = []
        async with client.aio.live.connect(model=model, config=config) as session:
            if text_input.strip() and audio_input is None:
                await session.send_client_content(
                    turns={"role": "user", "parts": [{"text": text_input.strip()}]},
                    turn_complete=True,
                )
            if audio_input is not None:
                pcm = audio_dict_to_pcm16(audio_input, target_rate=16000)
                if pcm:
                    from google.genai import types
                    # Live API accepts raw 16-bit PCM at 16 kHz.
                    await session.send_realtime_input(
                        audio=types.Blob(data=pcm, mime_type="audio/pcm;rate=16000")
                    )

            if audio_input is not None and text_input.strip():
                # Add optional text context after the audio without creating a second
                # synthetic empty user turn. The audio itself remains realtime input.
                await session.send_realtime_input(text=text_input.strip())

            async for message in session.receive():
                server_content = getattr(message, "server_content", None)
                if not server_content:
                    continue
                model_turn = getattr(server_content, "model_turn", None)
                if model_turn:
                    for part in getattr(model_turn, "parts", []) or []:
                        inline = getattr(part, "inline_data", None)
                        if inline and getattr(inline, "data", None):
                            data = inline.data
                            audio_chunks.append(data if isinstance(data, bytes) else bytes(data))
                transcript = getattr(server_content, "output_transcription", None)
                if transcript and getattr(transcript, "text", None):
                    transcript_chunks.append(transcript.text)
                if getattr(server_content, "turn_complete", False):
                    break

        return b"".join(audio_chunks), "".join(transcript_chunks)

    def chat(
        self,
        text_input,
        system_prompt,
        model="gemini-3.8-live",
        audio_input=None,
        voice="Kore",
        api_key="",
        proxy="",
        fallback_enabled=True,
    ):
        placeholder = {"waveform": torch.zeros((1, 1, 24000)), "sample_rate": 24000}
        if not HAS_GENAI:
            return placeholder, "Error: google-genai is not installed", ""
        key = get_api_key(api_key)
        if not key:
            return placeholder, "Error: No Gemini API key", ""
        try:
            client = build_client(key, proxy)
        except Exception as exc:
            return placeholder, f"Error initializing Gemini client: {exc}", ""

        candidates = [model] + [m for m in LIVE_MODELS if m != model]
        last_error = None
        for idx, candidate in enumerate(candidates if fallback_enabled else [model]):
            try:
                # ComfyUI executes nodes inside an event loop; run the async Live
                # session in a dedicated worker thread to avoid nested asyncio.run().
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        asyncio.run,
                        asyncio.wait_for(
                            self._run_session(client, candidate, text_input, system_prompt, audio_input, voice),
                            timeout=180.0,
                        ),
                    )
                    audio_bytes, transcript = future.result()
                if not audio_bytes and not transcript:
                    raise RuntimeError("Live API returned no audio or transcript.")
                audio = pcm16_to_audio(audio_bytes, 24000, 1)
                info = {
                    "requested_model": model,
                    "actual_model": candidate,
                    "fallback_used": idx > 0,
                    "voice": voice,
                    "input_has_audio": audio_input is not None,
                    "status": "completed",
                }
                return audio, transcript, json.dumps(info, ensure_ascii=False, indent=2)
            except Exception as exc:
                last_error = exc
                print(f"[Gemini Live Audio] {candidate} failed: {exc}")
                if not fallback_enabled or (not is_transient(exc) and not is_model_unavailable(exc)):
                    break

        return placeholder, f"Error: {last_error}", json.dumps({
            "requested_model": model,
            "status": "failed",
        }, ensure_ascii=False, indent=2)
