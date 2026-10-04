# Changelog

## v2.0.6 — TTS Pro controls and current Gemini 3.8 voices

- Reworked `Gemini TTS` around the current Gemini 3.8 Flash TTS / Flash-Lite TTS API.
- Added structured controls for language, accent, emotion, style, narration mode, pace, pitch and speaker profiles.
- Added 30 documented prebuilt studio voices, plus support for Extended Voice Library / Voice Design / Voice Replication IDs through `custom_voice_id`.
- Added custom style, narration, profile, pace and pitch instructions.
- Added inline vocal-tag support for `<laugh>`, `<sigh>`, `<breath>`, `<short pause>`, `<long pause>` and related human vocal events.
- Kept the v2.0.5 `speed` and `pitch` inputs for workflow compatibility, translating them into natural-language guidance instead of pretending they are native numeric API controls.
- Kept automatic TTS retry/fallback between Flash TTS and Flash-Lite TTS.
- Improved WAV detection/decoding for the current default `audio/wav` output.
- Updated package version to 2.0.6.

# Changelog

## v2.0.5 — Audio Recorder queue fix

- Restored the native **Start Record** button for `Gemini Audio Recorder`.
- Fixed `prompt_no_outputs` by marking the recorder as a valid ComfyUI `OUTPUT_NODE`.
- The button now increments the hidden `trigger` widget and queues the current workflow via the ComfyUI app queue API.
- Added duplicate-click protection while a recording run is being queued/executed.
- Button is UI-only and excluded from workflow/API serialization.
- The control remains a native canvas widget and therefore follows node resizing instead of floating over the canvas.

## 2.0.0 — 2026-10-02

- Rebuilt the Gemini node stack around the current Google Gemini API catalog.
- Added a shared retry/fallback router with 408/429/5xx handling, exponential backoff, jitter and per-model cooldown.
- Permanent 400/401/403 errors are surfaced immediately; unavailable model IDs can fall through to the next configured model.
- Disabled automatic function calling (AFC) explicitly in the core generate-content configuration.
- Switched Gemini 3.8 TTS to the documented Interactions API.
- Replaced legacy text/live/TTS model IDs with current catalog entries.
- Added actual Veo MP4 download/decoding and Omni 1.1 Flash video support.
- Replaced the audio-chat placeholder with a real Gemini Live WebSocket session.
- Fixed the recorder's selected-device handling and maximum-duration guard.
- Added safe output-size downgrades when a fallback model has a smaller documented output envelope.
- Added local unit tests for fallback ordering and error classification.


## v2.0.1 — Nano Banana UI update

- Image model dropdown now uses the current Google names: Nano Banana Pro, Nano Banana 2, Nano Banana 2 Lite.
- Official Gemini API IDs are preserved internally.
- Image fallback is ordered Pro → 2 → 2 Lite.
- Lite image fallback automatically forces 1K because 2K/4K are unsupported.
- Added current common aspect ratios exposed by the Gemini image API.

