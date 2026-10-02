"""Gemini 3.8 TTS node using the current Interactions API."""
from __future__ import annotations

import io
import json
import wave

import numpy as np
import torch

from .gemini_common import (
    HAS_GENAI,
    TTS_MODELS,
    build_client,
    fallback_chain,
    get_api_key,
    interaction_audio_bytes,
    pcm16_to_audio,
    run_with_fallback,
)


class GeminiTTS:
    TTS_MODELS = TTS_MODELS
    VOICES = [
        "Puck", "Charon", "Kore", "Fenrir",
        "Leda", "Orus", "Aoede", "Callirhoe",
    ]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": "Hello, this is a Gemini 3.8 TTS test."}),
                "model": (cls.TTS_MODELS, {"default": "gemini-3.8-flash-tts"}),
                "voice": (cls.VOICES, {"default": "Kore"}),
            },
            "optional": {
                "style": ("STRING", {"multiline": True, "default": "Natural, clear, expressive narration."}),
                "speed": ("FLOAT", {"default": 1.0, "min": 0.5, "max": 2.0, "step": 0.05}),
                "pitch": ("FLOAT", {"default": 0.0, "min": -10.0, "max": 10.0, "step": 0.5}),
                "api_key": ("STRING", {"default": ""}),
                "proxy": ("STRING", {"default": ""}),
                "fallback_enabled": ("BOOLEAN", {"default": True}),
                "retries_per_model": ("INT", {"default": 1, "min": 0, "max": 4, "step": 1}),
                "cooldown_seconds": ("FLOAT", {"default": 30.0, "min": 0.0, "max": 300.0, "step": 1.0}),
            },
        }

    RETURN_TYPES = ("AUDIO", "STRING")
    RETURN_NAMES = ("audio", "tts_info")
    FUNCTION = "generate_speech"
    CATEGORY = "Gemini 3.x"

    @classmethod
    def _candidate_models(cls, selected: str) -> list[str]:
        return fallback_chain(selected, cls.TTS_MODELS)

    @staticmethod
    def _decode_audio(data: bytes, mime: str):
        mime_l = (mime or "").lower()
        if "l16" in mime_l or "pcm" in mime_l:
            rate = 24000
            match = "rate="
            if match in mime_l:
                try:
                    rate = int(mime_l.split(match, 1)[1].split(";", 1)[0])
                except Exception:
                    pass
            return pcm16_to_audio(data, rate, 1)
        if "wav" in mime_l:
            try:
                with wave.open(io.BytesIO(data), "rb") as wf:
                    channels = wf.getnchannels()
                    rate = wf.getframerate()
                    raw = wf.readframes(wf.getnframes())
                arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                if channels > 1:
                    arr = arr.reshape(-1, channels).T.mean(axis=0)
                return {"waveform": torch.from_numpy(arr.copy()).reshape(1, 1, -1), "sample_rate": rate}
            except Exception:
                pass
        return pcm16_to_audio(data, 24000, 1)

    def generate_speech(
        self,
        text,
        model,
        voice,
        style="Natural, clear, expressive narration.",
        speed=1.0,
        pitch=0.0,
        api_key="",
        proxy="",
        fallback_enabled=True,
        retries_per_model=1,
        cooldown_seconds=30.0,
    ):
        placeholder = {"waveform": torch.zeros((1, 1, 24000)), "sample_rate": 24000}
        if not HAS_GENAI:
            return placeholder, "Error: google-genai is not installed"
        key = get_api_key(api_key)
        if not key:
            return placeholder, "Error: No Gemini API key"
        try:
            client = build_client(key, proxy)
        except Exception as exc:
            return placeholder, f"Error initializing Gemini client: {exc}"

        spoken_style = style.strip() or "Natural, clear, expressive narration."
        spoken_style += f" Pace approximately {float(speed):.2f}x."
        if abs(float(pitch)) > 0.001:
            spoken_style += f" Use a pitch impression of {float(pitch):+.1f} semitone(s)."

        # Google documents Gemini 3.8 TTS through the Interactions API. The text is
        # kept verbatim; delivery instructions live in speech_metadata annotations.
        interaction_input = [{
            "type": "user_input",
            "content": [{
                "type": "text",
                "text": text,
                "annotations": [{
                    "type": "speech_metadata",
                    "style": spoken_style,
                }],
            }],
        }]

        def request(current_model):
            return client.interactions.create(
                model=current_model,
                input=interaction_input,
                response_format={"type": "audio"},
                generation_config={
                    "speech_config": [
                        {"voice": voice},
                    ],
                },
            )

        try:
            interaction, actual_model, fallback_used = run_with_fallback(
                self._candidate_models(model),
                request,
                retries_per_model=retries_per_model,
                cooldown_seconds=cooldown_seconds,
                fallback_enabled=fallback_enabled,
                log_prefix="[Gemini TTS]",
            )
        except Exception as exc:
            return placeholder, f"Error: {exc}"

        audio_bytes, mime = interaction_audio_bytes(interaction)
        if not audio_bytes:
            return placeholder, "Error: Gemini returned no audio data"
        audio = self._decode_audio(audio_bytes, mime or "audio/wav")
        info = {
            "requested_model": model,
            "actual_model": actual_model,
            "fallback_used": fallback_used,
            "voice": voice,
            "style": spoken_style,
            "speed_guidance": speed,
            "pitch_guidance": pitch,
            "mime_type": mime,
            "sample_rate": audio["sample_rate"],
            "duration_sec": audio["waveform"].shape[-1] / audio["sample_rate"],
            "text_length": len(text),
        }
        return audio, json.dumps(info, ensure_ascii=False, indent=2)
