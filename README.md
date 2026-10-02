# ComfyUI-Gemini_3x_Pro v2.0

Advanced Gemini 3.x / Nano Banana / Veo / Omni nodes for ComfyUI, updated for the current Google Gemini API model catalog available in October 2026.

## What changed in v2.0

- Automatic fallback for transient API failures (`408`, `429`, `500`, `502`, `503`, `504`).
- Exponential backoff with jitter and bounded retries.
- Short per-model cooldown after repeated temporary failures, so an overloaded model is skipped on the next request for a short period.
- The selected model is always tried first; fallback proceeds downward through the configured family.
- Authentication/client errors such as `401` and `403` are not blindly retried.
- Explicit automatic function calling (AFC) is disabled for the core node, removing the SDK AFC warning when ordinary `generate_content` is used. Search grounding remains available as a server-side built-in tool.
- Current text model IDs: Gemini 3.8 Flash, 3.7 Flash, 3.6 Flash, 3.5 Flash, 3.5 Flash-Lite, 3.1 Flash-Lite, plus Gemini 3.1 Pro Preview.
- Current image model IDs: Nano Banana Pro, Nano Banana 2, Nano Banana 2 Lite.
- Current TTS model IDs: Gemini 3.8 Flash TTS and Gemini 3.8 Flash-Lite TTS.
- Current Live API model IDs: Gemini 3.8 Live and Gemini 3.8 Live Extended Thinking.
- Current video choices: Veo 3.1, Veo 3.1 Fast, Veo 3.1 Lite, and Gemini Omni 1.1 Flash.
- Video node now actually saves generated MP4 files and decodes them to ComfyUI IMAGE frames when `ffmpeg` is available.
- Live Audio Chat is no longer a placeholder: it creates a real Live API WebSocket session for each node execution.
- Audio recorder now honors the selected input device and enforces a configurable maximum duration.
- Structured JSON and Google Search grounding remain supported.

## Current model catalog used by this release

| Family | Models |
|---|---|
| Text / multimodal | `gemini-3.8-flash`, `gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, `gemini-3.1-pro-preview` |
| Image | `gemini-3-pro-image`, `gemini-3.1-flash-image`, `gemini-3.1-flash-lite-image` |
| TTS | `gemini-3.8-flash-tts`, `gemini-3.8-flash-lite-tts` |
| Live | `gemini-3.8-live`, `gemini-3.8-live-extended-thinking` |
| Video | `veo-3.1-generate-preview`, `veo-3.1-fast-generate-preview`, `veo-3.1-lite-generate-preview`, `gemini-omni-1.1-flash` |

The model list is based on Google's current Gemini API model page, last updated 1 October 2026. Stable models are preferred for production; preview endpoints are retained only where Google's current catalog still lists them. See the official links below.

## Fallback behavior

### Text / multimodal

```text
gemini-3.8-flash
    ↓ transient error
 gemini-3.7-flash
    ↓
gemini-3.6-flash
    ↓
gemini-3.5-flash
    ↓
gemini-3.5-flash-lite
    ↓
gemini-3.1-flash-lite
```

When `gemini-3.1-pro-preview` is selected, v2 tries Pro first and then falls back into the Flash family.

### Image

```text
gemini-3-pro-image
    ↓
gemini-3.1-flash-image
    ↓
gemini-3.1-flash-lite-image
```

### TTS

```text
gemini-3.8-flash-tts
    ↓
gemini-3.8-flash-lite-tts
```

### Video

```text
veo-3.1-generate-preview
    ↓
veo-3.1-fast-generate-preview
    ↓
veo-3.1-lite-generate-preview
    ↓
gemini-omni-1.1-flash
```

When Omni is selected, v2 tries Omni first and then falls back to Veo Fast/Lite.

## Retry policy

The plugin retries only transient failures. `401`, `403`, normal `400` request errors, and other permanent client errors are surfaced immediately. A model-not-found/unavailable error is treated as a model fallback signal.

Default values:

```text
retries_per_model = 1
cooldown_seconds = 30
backoff initial = 1.5s
backoff max = 12s
```

The exact sleep includes random jitter to avoid synchronized retry bursts.

## AFC

The core multimodal node explicitly sets:

```python
AutomaticFunctionCallingConfig(disable=True)
```

The node does not expose local Python functions as model tools, so AFC is not needed for ordinary multimodal analysis. Google Search grounding remains an explicit server-side tool option.

## Installation

1. Remove or rename the old `ComfyUI-Gemini_3x_Pro` directory.
2. Extract this folder as:

```text
ComfyUI/custom_nodes/ComfyUI-Gemini_3x_Pro
```

3. Put your Gemini API key into `config.json` or set `GEMINI_API_KEY` in the environment.
4. With portable ComfyUI, install dependencies using its embedded Python:

```bat
python_embeded\\python.exe -m pip install -r ComfyUI\\custom_nodes\\ComfyUI-Gemini_3x_Pro\\requirements.txt
```

5. Restart ComfyUI.

## Configuration

`config.json` contains safe defaults and no real key:

```json
{
  "GEMINI_API_KEY": "your_api_key_here",
  "DEFAULT_MODEL": "gemini-3.8-flash",
  "DEFAULT_IMAGE_MODEL": "gemini-3.1-flash-image",
  "DEFAULT_VIDEO_MODEL": "veo-3.1-generate-preview",
  "DEFAULT_TTS_MODEL": "gemini-3.8-flash-tts",
  "DEFAULT_LIVE_MODEL": "gemini-3.8-live",
  "PROXY": "",
  "FALLBACK_ENABLED": true,
  "RETRIES_PER_MODEL": 1,
  "COOLDOWN_SECONDS": 30,
  "BACKOFF_INITIAL_SECONDS": 1.5,
  "BACKOFF_MAX_SECONDS": 12,
  "SDK_RETRY_ATTEMPTS": 1
}
```

## Nodes

### 🧠 Gemini 3.x Pro Multimodal v2

Text + image + audio + ComfyUI video-frame input. Supports analysis, persistent chat, structured JSON and optional Google Search grounding.

Important: the `video` input is retained for workflow compatibility and represents an IMAGE tensor of sampled frames; it is not a true video upload. For actual video generation, use the Video node.

### 🎨 Gemini Image Generation v2

Uses Nano Banana image models through the current Interactions API. Supports reference images, aspect ratio, 1K/2K/4K response size, and sequential generation of up to four requested images.

### 🎬 Gemini Video Generation v2

Supports Veo 3.1 family and Gemini Omni 1.1 Flash. Veo uses the standard asynchronous video operation flow and Omni uses Interactions API.

The node stores the MP4 in ComfyUI's temp directory and exposes its local path in `video_info`. When `ffmpeg`/`ffprobe` are available, it also returns a decoded IMAGE batch.

### 🔊 Gemini Text-to-Speech v2

Uses current Gemini 3.8 TTS models. The node requests 24 kHz PCM for deterministic decoding and supports style instructions, voice selection, speed and pitch guidance.

### 🎙️ Gemini Live Audio Chat v2

Uses `gemini-3.8-live` or `gemini-3.8-live-extended-thinking` through the asynchronous Live API. Each execution opens a short-lived Live session, sends text and/or audio, collects audio output and output transcription, and closes the session.

### 🎤 Audio Recorder Gemini v2

Microphone recorder with device selection, silence stop, and maximum-duration protection.

### 📸 Multi Images Input v2

Combines up to 16 image inputs into one batched IMAGE tensor.

## Compatibility

The package targets ComfyUI Python environments that already provide PyTorch. `torch`/`torchaudio` are deliberately not installed by this package so a portable CUDA environment is not overwritten.

`google-genai` is pinned to the 2.x line:

```text
google-genai>=2.27.0,<3.0
```

## Troubleshooting

### `401 UNAUTHENTICATED`

The request is not authenticated. Recreate/verify the Google AI Studio API key and ensure the node is actually reading the intended key. v2 does not retry authentication failures.

### `503 UNAVAILABLE`

This is treated as a transient capacity/backend issue. v2 retries the selected model and then switches to the next fallback model automatically.

### `429 RESOURCE_EXHAUSTED`

Also treated as transient. v2 backs off and then switches models when required.

### Video returns a placeholder frame

The MP4 was generated successfully, but `ffmpeg`/`ffprobe` are not visible to the ComfyUI process. The real local MP4 path remains available in `video_info`.

### Live Audio Chat fails

Check that `websockets` is installed through `google-genai`, the API key is valid, and outbound WebSocket traffic is allowed by your network/proxy.

## Official documentation used for v2

- Gemini models: https://ai.google.dev/gemini-api/docs/models
- Gemini 3.8 Flash: https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash
- Image generation / Nano Banana: https://ai.google.dev/gemini-api/docs/image-generation
- Veo 3.1: https://ai.google.dev/gemini-api/docs/veo
- Gemini Omni Flash: https://ai.google.dev/gemini-api/docs/omni
- TTS: https://ai.google.dev/gemini-api/docs/speech-generation
- Live API: https://ai.google.dev/gemini-api/docs/live-api/get-started-sdk
- Deprecations: https://ai.google.dev/gemini-api/docs/deprecations
- Google GenAI Python SDK: https://googleapis.github.io/python-genai/

## License

Apache-2.0. See `LICENSE`.

### Audio Recorder queue fix (v2.0.5)

`Gemini Audio Recorder` is a valid `OUTPUT_NODE`. The **🔴 Start Record** button increments the serialized `trigger` input and queues the current workflow through the ComfyUI app queue API, avoiding `prompt_no_outputs` when the recorder is the only output node. The button is a native canvas widget and follows node resizing.
