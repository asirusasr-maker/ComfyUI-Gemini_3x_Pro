"""Gemini 3.8 TTS Pro node.

Uses the current Gemini 3.8 TTS Interactions API with structured
speech_metadata, inline vocal tags, prebuilt/extended/custom voices,
speaker profiles, and automatic model fallback.
"""
from __future__ import annotations

import io
import json
import re
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

    # Google currently documents 30 curated prebuilt studio voices.
    VOICES = [
        "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus",
        "Aoede", "Callirrhoe", "Autonoe", "Enceladus", "Iapetus",
        "Umbriel", "Algieba", "Despina", "Erinome", "Algenib",
        "Rasalgethi", "Laomedeia", "Achernar", "Alnilam", "Schedar",
        "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi",
        "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat",
    ]

    LANGUAGES = [
        "Auto Detect", "English", "Russian", "Uzbek", "Spanish", "French",
        "German", "Italian", "Portuguese", "Chinese", "Japanese", "Korean",
        "Arabic", "Hindi", "Turkish", "Dutch", "Polish", "Ukrainian",
        "Indonesian", "Vietnamese", "Thai", "Hebrew", "Greek",
        "Other / Custom",
    ]

    ACCENTS = [
        "Auto",
        "American English",
        "British English",
        "Australian English",
        "Indian English",
        "Irish English",
        "Scottish English",
        "Russian",
        "Uzbek",
        "French",
        "German",
        "Spanish",
        "Italian",
        "Custom",
    ]

    EMOTIONS = [
        "Neutral", "Calm", "Warm", "Friendly", "Happy", "Excited",
        "Dramatic", "Sad", "Angry", "Mysterious", "Serious",
        "Suspenseful", "Documentary", "Luxury", "Energetic", "Whispered",
        "Sarcastic", "Reassuring", "Urgent", "Custom",
    ]

    STYLES = [
        "Natural", "Conversational", "Narration", "Documentary",
        "Cinematic", "Audiobook", "Podcast", "News", "YouTube",
        "Commercial", "Luxury", "Trailer", "Storytelling",
        "Character", "ASMR-like", "Custom",
    ]

    NARRATION_MODES = [
        "Natural",
        "Narrator",
        "Documentary",
        "News Anchor",
        "YouTube Creator",
        "Audiobook",
        "Podcast",
        "Commercial",
        "Cinematic Trailer",
        "Character Performance",
        "Conversation",
        "Custom",
    ]

    PACES = [
        "Natural",
        "Very Slow",
        "Slow",
        "Relaxed",
        "Fast",
        "Very Fast",
        "Custom",
    ]

    PITCHES = [
        "Natural",
        "Low",
        "Medium",
        "High",
        "Very High",
        "Monotone",
        "Custom",
    ]

    SPEAKER_PROFILES = [
        "None",
        "Documentary Male",
        "Documentary Female",
        "YouTube Narrator",
        "Luxury Commercial",
        "News Presenter",
        "Audiobook Storyteller",
        "Cinematic Trailer",
        "Podcast Host",
        "Warm Explainer",
        "Custom",
    ]

    INLINE_TAG_RE = re.compile(
        r"<(?:laugh|sigh|cough|breath|short pause|long pause|"
        r"throat-clearing|chuckle|gasp|groan|cry|whimper|"
        r"sniff|yawn|hum|singing|whispering)>",
        re.IGNORECASE,
    )

    PROFILE_STYLES = {
        "None": "",
        "Documentary Male": "professional documentary narrator, mature and authoritative delivery",
        "Documentary Female": "professional documentary narrator, warm and authoritative delivery",
        "YouTube Narrator": "engaging YouTube narration, natural and confident delivery",
        "Luxury Commercial": "premium luxury commercial voice, polished, elegant and controlled delivery",
        "News Presenter": "clear broadcast-news delivery, precise articulation and confident pacing",
        "Audiobook Storyteller": "immersive audiobook storytelling, expressive but natural character delivery",
        "Cinematic Trailer": "cinematic trailer narration, dramatic controlled intensity and deliberate emphasis",
        "Podcast Host": "natural podcast host delivery, conversational and personable",
        "Warm Explainer": "warm educational explainer delivery, clear, friendly and reassuring",
        "Custom": "",
    }

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "Hello, this is a Gemini 3.8 TTS Pro test.",
                    },
                ),
                "model": (cls.TTS_MODELS, {"default": "gemini-3.8-flash-tts"}),
                "voice": (cls.VOICES, {"default": "Kore"}),
                "language": (cls.LANGUAGES, {"default": "Auto Detect"}),
                "emotion": (cls.EMOTIONS, {"default": "Neutral"}),
                "style_preset": (cls.STYLES, {"default": "Natural"}),
                "narration_mode": (cls.NARRATION_MODES, {"default": "Natural"}),
                "speaker_profile": (cls.SPEAKER_PROFILES, {"default": "None"}),
                "pace": (cls.PACES, {"default": "Natural"}),
                "pitch_mode": (cls.PITCHES, {"default": "Natural"}),
            },
            "optional": {
                "custom_voice_id": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Optional Extended Voice Library, Voice Design (voice_...) or Voice Replication ID. Overrides the prebuilt Voice.",
                    },
                ),
                "custom_language": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Used when Language is Other / Custom.",
                    },
                ),
                "accent": (cls.ACCENTS, {"default": "Auto"}),
                "custom_accent": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Used when Accent is Custom.",
                    },
                ),
                "custom_emotion": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Used when Emotion is Custom.",
                    },
                ),
                "custom_style": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "tooltip": "Extra turn-level delivery instructions sent through speech_metadata.style.",
                    },
                ),
                "custom_narration": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "tooltip": "Additional narration direction.",
                    },
                ),
                "custom_profile": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "tooltip": "Custom reusable speaker persona/delivery description.",
                    },
                ),
                "inline_vocal_tags": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "Keep supported <laugh>, <sigh>, <breath>, <short pause>, etc. in the transcript.",
                    },
                ),
                "custom_pace": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Used when Pace is Custom, e.g. 'speaking at a relaxed pace'.",
                    },
                ),
                "custom_pitch": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Used when Pitch is Custom, e.g. 'slightly low pitch with warm inflection'.",
                    },
                ),
                # Backward-compatible controls from v2.0.5. They are now translated
                # into style guidance instead of pretending to be native numeric API controls.
                "speed": (
                    "FLOAT",
                    {
                        "default": 1.0,
                        "min": 0.5,
                        "max": 2.0,
                        "step": 0.05,
                        "tooltip": "Legacy compatibility control. Converted to natural-language pace guidance.",
                    },
                ),
                "pitch": (
                    "FLOAT",
                    {
                        "default": 0.0,
                        "min": -10.0,
                        "max": 10.0,
                        "step": 0.5,
                        "tooltip": "Legacy compatibility control. Converted to natural-language pitch guidance.",
                    },
                ),
                "api_key": ("STRING", {"default": ""}),
                "proxy": ("STRING", {"default": ""}),
                "fallback_enabled": ("BOOLEAN", {"default": True}),
                "retries_per_model": ("INT", {"default": 1, "min": 0, "max": 4, "step": 1}),
                "cooldown_seconds": (
                    "FLOAT",
                    {"default": 30.0, "min": 0.0, "max": 300.0, "step": 1.0},
                ),
            },
        }

    RETURN_TYPES = ("AUDIO", "STRING")
    RETURN_NAMES = ("audio", "tts_info")
    FUNCTION = "generate_speech"
    CATEGORY = "Gemini 3.x"

    @classmethod
    def _candidate_models(cls, selected: str) -> list[str]:
        return fallback_chain(selected, cls.TTS_MODELS)

    @classmethod
    def _build_style(
        cls,
        *,
        language: str,
        custom_language: str,
        accent: str,
        custom_accent: str,
        emotion: str,
        custom_emotion: str,
        style_preset: str,
        custom_style: str,
        narration_mode: str,
        custom_narration: str,
        speaker_profile: str,
        custom_profile: str,
        pace: str,
        custom_pace: str,
        pitch_mode: str,
        custom_pitch: str,
        legacy_speed: float,
        legacy_pitch: float,
    ) -> str:
        parts: list[str] = []

        profile = (
            custom_profile.strip()
            if speaker_profile == "Custom"
            else cls.PROFILE_STYLES.get(speaker_profile, "")
        )
        if profile:
            parts.append(profile)

        if language == "Other / Custom":
            if custom_language.strip():
                parts.append(f"spoken in {custom_language.strip()}")
        elif language != "Auto Detect":
            parts.append(f"spoken in {language}")

        if accent == "Custom":
            if custom_accent.strip():
                parts.append(f"{custom_accent.strip()} accent")
        elif accent != "Auto":
            parts.append(f"{accent} accent")

        if emotion == "Custom":
            if custom_emotion.strip():
                parts.append(custom_emotion.strip())
        elif emotion != "Neutral":
            parts.append(f"{emotion.lower()} emotional tone")

        if style_preset == "Custom":
            if custom_style.strip():
                parts.append(custom_style.strip())
        elif style_preset != "Natural":
            parts.append(f"{style_preset.lower()} style")

        if narration_mode == "Custom":
            if custom_narration.strip():
                parts.append(custom_narration.strip())
        elif narration_mode != "Natural":
            parts.append(f"{narration_mode.lower()} delivery")

        if pace == "Custom":
            if custom_pace.strip():
                parts.append(custom_pace.strip())
        else:
            pace_map = {
                "Very Slow": "speaking very slowly",
                "Slow": "speaking slowly",
                "Relaxed": "speaking at a relaxed pace",
                "Fast": "speaking rapidly",
                "Very Fast": "speaking very rapidly",
            }
            if pace in pace_map:
                parts.append(pace_map[pace])

        if pitch_mode == "Custom":
            if custom_pitch.strip():
                parts.append(custom_pitch.strip())
        else:
            pitch_map = {
                "Low": "low pitch",
                "Medium": "medium pitch",
                "High": "high pitch",
                "Very High": "very high pitch",
                "Monotone": "monotone and flat inflection",
            }
            if pitch_mode in pitch_map:
                parts.append(pitch_map[pitch_mode])

        # Preserve the old controls so existing v2.0.5 workflows keep their meaning.
        if abs(float(legacy_speed) - 1.0) > 0.001:
            if legacy_speed < 0.9:
                parts.append("slower overall pacing")
            elif legacy_speed > 1.1:
                parts.append("faster overall pacing")
        if abs(float(legacy_pitch)) > 0.001:
            if legacy_pitch < 0:
                parts.append("slightly lower pitch")
            else:
                parts.append("slightly higher pitch")

        return ", ".join(p for p in parts if p).strip()

    @classmethod
    def _decode_audio(cls, data: bytes, mime: str):
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

        if "wav" in mime_l or data[:4] == b"RIFF":
            try:
                with wave.open(io.BytesIO(data), "rb") as wf:
                    channels = wf.getnchannels()
                    rate = wf.getframerate()
                    raw = wf.readframes(wf.getnframes())
                arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                if channels > 1:
                    arr = arr.reshape(-1, channels).T.mean(axis=0)
                return {
                    "waveform": torch.from_numpy(arr.copy()).reshape(1, 1, -1),
                    "sample_rate": rate,
                }
            except Exception:
                pass

        return pcm16_to_audio(data, 24000, 1)

    def generate_speech(
        self,
        text,
        model,
        voice,
        language="Auto Detect",
        emotion="Neutral",
        style_preset="Natural",
        narration_mode="Natural",
        speaker_profile="None",
        pace="Natural",
        pitch_mode="Natural",
        custom_voice_id="",
        custom_language="",
        accent="Auto",
        custom_accent="",
        custom_emotion="",
        custom_style="",
        custom_narration="",
        custom_profile="",
        inline_vocal_tags=True,
        custom_pace="",
        custom_pitch="",
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

        transcript = text if inline_vocal_tags else self.INLINE_TAG_RE.sub("", text)

        spoken_style = self._build_style(
            language=language,
            custom_language=custom_language,
            accent=accent,
            custom_accent=custom_accent,
            emotion=emotion,
            custom_emotion=custom_emotion,
            style_preset=style_preset,
            custom_style=custom_style,
            narration_mode=narration_mode,
            custom_narration=custom_narration,
            speaker_profile=speaker_profile,
            custom_profile=custom_profile,
            pace=pace,
            custom_pace=custom_pace,
            pitch_mode=pitch_mode,
            custom_pitch=custom_pitch,
            legacy_speed=speed,
            legacy_pitch=pitch,
        )

        content = {
            "type": "text",
            "text": transcript,
            "annotations": [
                {
                    "type": "speech_metadata",
                    "style": spoken_style,
                }
            ],
        }

        interaction_input = [
            {
                "type": "user_input",
                "content": [content],
            }
        ]

        selected_voice = custom_voice_id.strip() or voice

        def request(current_model):
            return client.interactions.create(
                model=current_model,
                input=interaction_input,
                response_format={"type": "audio"},
                generation_config={
                    "speech_config": [
                        {"voice": selected_voice},
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
                log_prefix="[Gemini TTS Pro]",
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
            "voice": selected_voice,
            "voice_source": "custom/extended" if custom_voice_id.strip() else "prebuilt",
            "language": language if language != "Other / Custom" else custom_language,
            "accent": accent if accent != "Custom" else custom_accent,
            "emotion": emotion if emotion != "Custom" else custom_emotion,
            "style_preset": style_preset,
            "narration_mode": narration_mode,
            "speaker_profile": speaker_profile,
            "pace": pace,
            "pitch_mode": pitch_mode,
            "inline_vocal_tags": inline_vocal_tags,
            "style": spoken_style,
            "mime_type": mime,
            "sample_rate": audio["sample_rate"],
            "duration_sec": audio["waveform"].shape[-1] / audio["sample_rate"],
            "text_length": len(transcript),
        }
        return audio, json.dumps(info, ensure_ascii=False, indent=2)
