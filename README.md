# 🧠 ComfyUI-Gemini_3x_Pro

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![ComfyUI](https://img.shields.io/badge/ComfyUI-0.33+-green.svg)](https://github.com/comfyanonymous/ComfyUI)
[![Google GenAI](https://img.shields.io/badge/google--genai-2.x-orange.svg)](https://pypi.org/project/google-genai/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

> **Advanced Gemini 3.x nodes for ComfyUI** — multimodal AI pipeline with text, image, audio, video, TTS, live chat, and audio recording. Built on the latest `google-genai` SDK (v2.x) with full support for Gemini 3.x series models.

---

## 📑 Table of Contents

- [Features](#-features)
- [Installation](#-installation)
- [Dependencies](#-dependencies)
- [API Key Setup](#-api-key-setup)
- [Nodes Overview](#-nodes-overview)
- [Available Models & Rate Limits](#-available-models--rate-limits)
- [Proxy Configuration](#-proxy-configuration)
- [Chat Mode](#-chat-mode)
- [Important Notes](#-important-notes)
- [Troubleshooting](#-troubleshooting)
- [License](#-license)

---

## ✨ Features

- 🧠 **Multimodal Analysis** — text + images + audio + video in a single prompt
- 🎨 **Native Image Generation** — Gemini Nano Banana models (requires Paid tier)
- 🎬 **Video Generation** — Veo 3.1 preview (requires Paid tier)
- 🔊 **Text-to-Speech** — 8 voices, raw PCM/L16/MP3 auto-detection
- 🎙️ **Live Audio Chat** — placeholder for real-time streaming
- 🎤 **Audio Recorder** — built-in microphone recording with silence detection
- 📸 **Multi Images Input** — aggregate up to 16 images into one batch
- 💬 **Persistent Chat Mode** — conversation history survives between workflow runs
- 🔍 **Search Grounding** — real-time Google Search integration (select models)
- 📐 **Structured JSON Output** — schema-validated responses

---

## 🚀 Installation

### Method 1: Git Clone (Recommended)

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/asirusasr-maker/ComfyUI-Gemini_3x_Pro.git
cd ComfyUI-Gemini_3x_Pro
```

For **portable** ComfyUI:
```bash
..\..\python_embeded\python.exe -m pip install -r requirements.txt
```

For **standard** ComfyUI:
```bash
pip install -r requirements.txt
```

### Method 2: ComfyUI Manager

1. Open ComfyUI → **Manager** → **Install Custom Nodes**
2. Click **Load From File** → select the downloaded ZIP
3. Restart ComfyUI

---

## 📦 Dependencies

All required packages are listed in `requirements.txt`:

```
google-genai>=2.0.0
pillow>=10.0.0
numpy>=1.24.0
sounddevice>=0.4.0
```

| Package | Version | Purpose |
|---------|---------|---------|
| `google-genai` | `>=2.0.0` | **Required.** Official Google GenAI SDK v2 |
| `pillow` | `>=10.0.0` | Image processing |
| `numpy` | `>=1.24.0` | Tensor operations |
| `sounddevice` | `>=0.4.0` | Microphone input (Audio Recorder) |

> 💡 `torch` and `torchaudio` are **not** in `requirements.txt` because ComfyUI already provides them. Installing them separately could overwrite your CUDA-enabled PyTorch with a CPU-only version.

---

## 🔑 API Key Setup

1. Go to **[Google AI Studio](https://aistudio.google.com/app/apikey)**
2. Click **"Create API Key"**
3. Copy the key

### Option A: Config File
Edit `config.json` in the node folder:
```json
{
    "GEMINI_API_KEY": "your_api_key_here"
}
```

### Option B: Environment Variable
```bash
set GEMINI_API_KEY=your_api_key_here
```

### Option C: Node Input
Paste the key directly into the `api_key` widget of any node.

---

## 🧩 Nodes Overview

> 📷 **Screenshots:** Place your node screenshots in `docs/images/` folder to match the paths below.

---

### 🧠 Gemini 3.x Pro Multimodal

<img src="docs/images/gemini_3x_pro.png" width="400" alt="Gemini 3.x Pro Multimodal">

The core multimodal node. Accepts **text, images, video, and audio** simultaneously.

**Inputs:**
| Name | Type | Description |
|------|------|-------------|
| `prompt` | STRING | Main text prompt |
| `images` | IMAGE | One or multiple images |
| `video` | IMAGE | Video frames (up to 16) |
| `audio` | AUDIO | Audio waveform (dict) |
| `system_instruction` | STRING | System prompt |
| `model` | COMBO | Select Gemini model |
| `operation_mode` | COMBO | `analysis` / `chat` / `structured_json` |
| `temperature` | FLOAT | 0.0 – 2.0 |
| `max_output_tokens` | INT | Up to 65536 |
| `use_search_grounding` | BOOLEAN | Enable Google Search |
| `chat_mode` | BOOLEAN | Enable persistent chat |
| `clear_history` | BOOLEAN | Reset conversation |
| `json_schema` | STRING | JSON schema for structured output |

**Outputs:** `generated_content`, `raw_response`, `usage_info`

---

### 🎨 Gemini Image Generation

<img src="docs/images/gemini_image_gen.png" width="400" alt="Gemini Image Generation">

Generates images using Google\'s **Nano Banana** models via the Interactions API.

**Inputs:**
| Name | Type | Description |
|------|------|-------------|
| `prompt` | STRING | Image description |
| `model` | COMBO | `gemini-3.1-flash-image`, `gemini-3-pro-image`, etc. |
| `aspect_ratio` | COMBO | `1:1`, `16:9`, `9:16`, `4:3`, `3:4`, `21:9` |
| `reference_image` | IMAGE | Style/character reference |
| `negative_prompt` | STRING | What to avoid |
| `num_images` | INT | 1 – 4 |

**Outputs:** `generated_images`, `generation_info`, `raw_response`

> ⚠️ **Requires Paid tier.** On Free tier the rate limit is `0/0` — the node will return a black placeholder.

---

### 🎬 Gemini Video Generation

<img src="docs/images/gemini_video_gen.png" width="400" alt="Gemini Video Generation">

Generates video clips using **Veo 3.1**.

**Inputs:**
| Name | Type | Description |
|------|------|-------------|
| `prompt` | STRING | Video description |
| `model` | COMBO | `veo-3.1-generate-preview`, `veo-3.1-lite-generate-preview` |
| `duration` | COMBO | `3s`, `5s`, `8s`, `10s` |
| `aspect_ratio` | COMBO | `16:9`, `9:16`, `1:1` |
| `reference_image` | IMAGE | First frame reference |

**Outputs:** `video_frames`, `video_info`, `raw_response`

> ⚠️ **Requires Paid tier.** Free tier has no access to Veo models.

---

### 🔊 Gemini Text-to-Speech

<img src="docs/images/gemini_tts.png" width="400" alt="Gemini TTS">

Converts text to speech using Gemini TTS models. Auto-detects `audio/l16`, `audio/mp3`, and `audio/wav` formats from API.

**Inputs:**
| Name | Type | Description |
|------|------|-------------|
| `text` | STRING | Text to speak |
| `model` | COMBO | `gemini-3.1-flash-tts-preview` |
| `voice` | COMBO | `Puck`, `Charon`, `Kore`, `Fenrir`, `Leda`, `Orus`, `Aoede`, `Callirhoe` |
| `speed` | FLOAT | Playback speed (0.5 – 2.0) |
| `pitch` | FLOAT | Pitch shift (-10 – +10) |

**Outputs:** `audio` (ComfyUI AUDIO dict), `tts_info`

---

### 🎙️ Gemini Live Audio Chat

<img src="docs/images/gemini_audio_chat.png" width="400" alt="Gemini Live Audio Chat">

Placeholder node for future **Live API** (WebSocket/async streaming) integration.

**Inputs:** `text_input`, `system_prompt`, `audio_input`

**Outputs:** `audio_output`, `text_response`, `session_info`

> 📝 Currently returns placeholder audio. Full implementation requires asyncio WebSocket.

---

### 🎤 Audio Recorder Gemini

<img src="docs/images/audio_recorder.png" width="400" alt="Audio Recorder">

Records audio from your microphone with **silence detection**. Click the **🎤 Start Recording** button — recording stops automatically after `silence_duration` seconds of silence (or 10 sec max).

**Inputs:**
| Name | Type | Description |
|------|------|-------------|
| `device` | COMBO | Microphone device |
| `sample_rate` | INT | 8000 – 96000 Hz |
| `silence_threshold` | FLOAT | Amplitude threshold (0.001 – 0.1) |
| `silence_duration` | FLOAT | Stop after N seconds of silence |

**Outputs:** `audio` (ComfyUI AUDIO dict)

---

### 📸 Multi Images Input

<img src="docs/images/multi_images.png" width="400" alt="Multi Images Input">

Aggregates up to **16 individual images** into a single batched tensor.

**Inputs:** `image_1` … `image_16` (optional)

**Outputs:** `images` (batched IMAGE tensor)

---

## 🚦 Available Models & Rate Limits

> All limits are for **Free tier** unless noted. Paid tier limits are significantly higher.

### 🧠 Text / Multimodal Models

| Model | RPM | TPM | RPD | Search Grounding | Status |
|-------|-----|-----|-----|------------------|--------|
| `gemini-3.7-flash` | 15 | 1M | 1500 | ❌ | ✅ GA |
| `gemini-3.6-flash` | 15 | 1M | 1500 | ❌ | ✅ GA |
| `gemini-3.5-flash` | 15 | 1M | 1500 | ❌ | ✅ GA |
| `gemini-3.5-flash-lite` | 15 | 1M | 1500 | ✅ 500/day | ✅ GA |
| `gemini-3.1-flash-lite` | 15 | 1M | 1500 | ❌ | ✅ GA |
| `gemini-3.1-pro` | 15 | 1M | 1500 | ❌ | ✅ GA |
| `gemini-3.1-flash-live-preview` | 15 | 1M | 1500 | ❌ | 🔬 Preview |
| `gemini-flash-latest` | 15 | 1M | 1500 | ❌ | ✅ Alias |
| `gemini-pro-latest` | 15 | 1M | 1500 | ❌ | ✅ Alias |

### 🎨 Image Generation (Nano Banana)

| Model | Free Tier | Paid Tier | Status |
|-------|-----------|-----------|--------|
| `gemini-3.1-flash-image` | **0/0** ❌ | ✅ ~$0.01–0.04/img | ✅ GA |
| `gemini-3-pro-image` | **0/0** ❌ | ✅ ~$0.01–0.04/img | ✅ GA |
| `gemini-3.1-flash-lite-image` | **0/0** ❌ | ✅ ~$0.01–0.04/img | ✅ GA |

> ⚠️ On Free tier these models return **429 RESOURCE_EXHAUSTED**. The node will output a black placeholder + error text instead of crashing.

### 🎬 Video Generation (Veo)

| Model | Free Tier | Paid Tier | Status |
|-------|-----------|-----------|--------|
| `veo-3.1-generate-preview` | **0/0** ❌ | ✅ Paid | 🔬 Preview |
| `veo-3.1-lite-generate-preview` | **0/0** ❌ | ✅ Paid | 🔬 Preview |
| `gemini-omni-flash` | **0/0** ❌ | ✅ Paid | 🔬 Preview |

### 🔊 Text-to-Speech

| Model | RPM | TPM | RPD | Status |
|-------|-----|-----|-----|--------|
| `gemini-3.1-flash-tts-preview` | 3 | 10K | 10 | 🔬 Preview |

---

## 🌐 Proxy Configuration

The `proxy` field allows routing API requests through an intermediary server.

**Why use a proxy?**
- **Regional blocks** — Google AI Studio may be unavailable in your country
- **Faster routing** — connect through a closer server
- **Privacy** — hide your direct IP

**Format:**
```
http://ip:port
http://user:pass@proxy.com:3128
```

Leave empty if Google API is directly accessible in your region.

---

## 💬 Chat Mode

Enable persistent conversations that **survive between workflow runs**.

### How to use

1. Set `chat_mode: true`
2. Send your first prompt → Gemini responds
3. **Change only the prompt** → keep `chat_mode: true`
4. Gemini remembers the previous context and answers accordingly
5. Set `clear_history: true` → Queue → starts a **fresh conversation**

### Example Workflow

| Step | Prompt | chat_mode | clear_history | Result |
|------|--------|-----------|---------------|--------|
| 1 | "Tell me about Uzbekistan" | true | false | Full description |
| 2 | "What is the capital?" | true | false | "Tashkent" (remembers context!) |
| 3 | "Explain quantum physics" | true | **true** | New topic, no memory of Uzbekistan |

> 📝 History is stored **per model** in RAM. If you restart ComfyUI, history resets.

---

## ⚠️ Important Notes

### 1. Image & Video Generation = Paid Only
As of August 2026, Google has set **0/0 rate limits** for Image Generation and Video Generation on the Free tier. You **must** attach a billing card in [Google AI Studio](https://aistudio.google.com/app/apikey) to use these features.

**Alternative for Free users:**
- Use **Stable Diffusion / SDXL / Flux** inside ComfyUI for images
- Use **MiniMax H3** or other local video models for video

### 2. Search Grounding Limitations
- `gemini-3.1-flash-lite` + Search Grounding = **429 error** on Free tier
- Use `gemini-3.5-flash-lite` or `gemini-2.0-flash` (if still active) for free search
- Or disable `use_search_grounding` entirely

### 3. Deprecated Parameters
For Gemini 3.x models, `temperature`, `top_p`, and `top_k` are marked **deprecated** by Google but still functional. They may be removed in future API versions.

### 4. Audio Format
The node accepts ComfyUI\'s native `AUDIO` dict (`{"waveform": tensor, "sample_rate": int}`). Audio is automatically converted to WAV and sent to Gemini as `types.Part.from_bytes()`.

---

## 🔧 Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| `google-genai not installed` | Missing dependency | `pip install -r requirements.txt` |
| `No API key` | Key not set | Add to `config.json` or node input |
| `429 Too Many Requests` | Rate limit exceeded | Wait 1 minute; check model limits |
| `429 with Image Gen` | Free tier blocked | Upgrade to Paid tier |
| `'dict' object has no attribute 'cpu'` | Old node version | Update to v14+ |
| `Input should be a valid dictionary` | Audio as dict not Part | Update to v14+ |
| Chat history resets | Different prompt changes hash | Update to v9+ (fixed session ID) |
| Black image output | Image Gen on Free tier | Normal — API limit is 0/0 |
| TTS returns silence | Audio format mismatch | Update to v7+ (L16/MP3/WAV support) |

---

## 📄 License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.

```
Copyright 2026 ComfyUI-Gemini_3x_Pro Contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

---

## 🙏 Credits

- Built on [Google GenAI SDK](https://github.com/googleapis/python-genai)
- Inspired by [ComfyUI-Gemini_Flash_2.0_Exp](https://github.com/ShmuelRonen/ComfyUI-Gemini_Flash_2.0_Exp) by ShmuelRonen
- Audio Recorder based on community nodes with silence detection

---

*Last updated: August 2026*
