"""Shared runtime helpers for ComfyUI-Gemini_3x_Pro v2.0."""
from __future__ import annotations

import base64
import io
import json
import os
import random
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Iterable

import numpy as np
import torch
from PIL import Image

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except Exception:
    genai = None  # type: ignore[assignment]
    types = None  # type: ignore[assignment]
    HAS_GENAI = False

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"

# Current model families checked against Google's Gemini API catalog on 2026-10-01.
FLASH_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
]
PRO_MODEL = "gemini-3.1-pro-preview"
# Nano Banana family (official Gemini API model IDs)
IMAGE_MODELS = [
    "gemini-3-pro-image",          # Nano Banana Pro
    "gemini-3.1-flash-image",      # Nano Banana 2
    "gemini-3.1-flash-lite-image", # Nano Banana 2 Lite
]
TTS_MODELS = [
    "gemini-3.8-flash-tts",
    "gemini-3.8-flash-lite-tts",
]
LIVE_MODELS = [
    "gemini-3.8-live",
    "gemini-3.8-live-extended-thinking",
]
VIDEO_MODELS = [
    "veo-3.1-generate-preview",
    "veo-3.1-fast-generate-preview",
    "veo-3.1-lite-generate-preview",
    "gemini-omni-1.1-flash",
]

RETRYABLE_CODES = {408, 429, 500, 502, 503, 504}
MODEL_FALLBACK_CODES = {404}
_AUTH_CODES = {400, 401, 403}

# Process-local health memory. This intentionally resets when ComfyUI restarts.
_MODEL_COOLDOWN: dict[str, float] = {}


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[Gemini 3.x Pro] Config read error: {exc}")
        return {}


def get_api_key(api_key_input: str = "") -> str:
    value = (api_key_input or "").strip()
    if value:
        return value
    config = load_config()
    value = str(config.get("GEMINI_API_KEY", "")).strip()
    if value and value != "your_api_key_here":
        return value
    return os.environ.get("GEMINI_API_KEY", "").strip()


def build_client(api_key: str, proxy: str = ""):
    """Create a GenAI client with SDK retry disabled by default.

    v2 owns retries/fallback centrally so a single HTTP failure cannot be hidden
    behind SDK-internal retry attempts before the node gets a chance to switch models.
    """
    if not HAS_GENAI:
        return None

    try:
        retry_options = types.HttpRetryOptions(attempts=1)
        if proxy and proxy.strip():
            http_options = types.HttpOptions(
                api_version="v1beta",
                base_url=proxy.strip(),
                retry_options=retry_options,
            )
        else:
            http_options = types.HttpOptions(retry_options=retry_options)
        return genai.Client(api_key=api_key, http_options=http_options)
    except Exception:
        # Keep compatibility with older 2.x builds.
        kwargs: dict[str, Any] = {"api_key": api_key}
        if proxy and proxy.strip():
            kwargs["http_options"] = {"api_version": "v1beta", "base_url": proxy.strip()}
        return genai.Client(**kwargs)


def exception_text(exc: Exception) -> str:
    return str(exc or "")


def get_status_code(exc: Exception) -> int | None:
    for attr in ("status_code", "code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    if response is not None:
        value = getattr(response, "status_code", None)
        if isinstance(value, int):
            return value
    match = re.search(r"\b(400|401|403|404|408|409|429|500|502|503|504)\b", exception_text(exc))
    return int(match.group(1)) if match else None


def is_transient(exc: Exception) -> bool:
    code = get_status_code(exc)
    if code in RETRYABLE_CODES:
        return True
    if code in _AUTH_CODES or code == 404:
        return False
    text = exception_text(exc).lower()
    return any(
        token in text
        for token in (
            "unavailable",
            "high demand",
            "temporarily unavailable",
            "resource exhausted",
            "rate limit",
            "too many requests",
            "deadline exceeded",
            "timeout",
            "temporarily overloaded",
        )
    )


def is_model_unavailable(exc: Exception) -> bool:
    if get_status_code(exc) in MODEL_FALLBACK_CODES:
        return True
    text = exception_text(exc).lower()
    return any(
        token in text
        for token in (
            "model not found",
            "model is not found",
            "not supported for this method",
            "model does not exist",
            "unknown model",
        )
    )


def fallback_chain(selected: str, chain: Iterable[str]) -> list[str]:
    models = list(dict.fromkeys(chain))
    if selected in models:
        return models[models.index(selected):]
    return [selected] + models


def model_on_cooldown(model: str) -> bool:
    until = _MODEL_COOLDOWN.get(model, 0.0)
    if until <= time.time():
        _MODEL_COOLDOWN.pop(model, None)
        return False
    return True


def mark_model_unhealthy(model: str, seconds: float) -> None:
    if seconds > 0:
        _MODEL_COOLDOWN[model] = time.time() + seconds


def run_with_fallback(
    models: Iterable[str],
    request: Callable[[str], Any],
    *,
    retries_per_model: int = 1,
    initial_delay: float = 1.5,
    max_delay: float = 12.0,
    cooldown_seconds: float = 30.0,
    fallback_enabled: bool = True,
    log_prefix: str = "[Gemini 3.x Pro]",
) -> tuple[Any, str, bool]:
    """Run request(model) with bounded transient retry and ordered model fallback."""
    candidates = list(dict.fromkeys(models))
    if not candidates:
        raise RuntimeError("No model candidates were supplied.")

    last_error: Exception | None = None
    attempts = max(1, int(retries_per_model) + 1)

    for index, model in enumerate(candidates):
        if model_on_cooldown(model):
            print(f"{log_prefix} Skipping {model}: cooldown is active.")
            continue

        if index > 0:
            print(f"{log_prefix} Fallback → {model}")

        for attempt in range(attempts):
            try:
                result = request(model)
                _MODEL_COOLDOWN.pop(model, None)
                print(f"{log_prefix} HTTP 200 OK → {model}")
                return result, model, index > 0
            except Exception as exc:
                last_error = exc
                code = get_status_code(exc)

                # Permanent errors must surface immediately. A different model will
                # not fix a malformed request or invalid credentials.
                if not is_model_unavailable(exc) and not is_transient(exc):
                    raise

                if is_model_unavailable(exc):
                    print(f"{log_prefix} {model} unavailable (HTTP {code or 'n/a'}); switching model.")
                    mark_model_unhealthy(model, cooldown_seconds)
                    break

                print(f"{log_prefix} {model} returned HTTP {code or 'transient error'}")
                if attempt >= attempts - 1:
                    mark_model_unhealthy(model, cooldown_seconds)
                    print(f"{log_prefix} {model} exhausted retries; switching model.")
                    break

                delay = min(initial_delay * (2 ** attempt), max_delay)
                delay += random.uniform(0.0, 0.75)
                print(f"{log_prefix} Retry {attempt + 1}/{attempts - 1} in {delay:.1f}s")
                time.sleep(delay)

        if not fallback_enabled:
            break

    if last_error:
        raise last_error
    raise RuntimeError("All Gemini model candidates are temporarily unavailable.")


def make_generate_config(
    *,
    temperature: float = 0.7,
    max_output_tokens: int = 8192,
    top_p: float = 0.95,
    top_k: int = 40,
    system_instruction: str = "",
    use_search_grounding: bool = False,
    response_mime_type: str | None = None,
    response_schema: Any | None = None,
):
    kwargs: dict[str, Any] = {
        "temperature": float(temperature),
        "max_output_tokens": int(max_output_tokens),
        "top_p": float(top_p),
        "top_k": int(top_k),
    }
    if system_instruction:
        kwargs["system_instruction"] = system_instruction
    if use_search_grounding:
        kwargs["tools"] = [types.Tool(google_search=types.GoogleSearch())]
    if response_mime_type:
        kwargs["response_mime_type"] = response_mime_type
    if response_schema is not None:
        kwargs["response_schema"] = response_schema

    # No Python function tools are exposed by this plugin; AFC is unnecessary.
    try:
        kwargs["automatic_function_calling"] = types.AutomaticFunctionCallingConfig(disable=True)
    except Exception:
        kwargs["automatic_function_calling"] = {"disable": True}

    return types.GenerateContentConfig(**kwargs)


def tensor_to_pil_list(image_tensor: Any, *, max_images: int | None = None) -> list[Image.Image]:
    if image_tensor is None:
        return []
    tensor = image_tensor.detach().cpu() if torch.is_tensor(image_tensor) else torch.as_tensor(image_tensor)
    if tensor.ndim == 3:
        tensor = tensor.unsqueeze(0)
    if tensor.ndim != 4:
        raise ValueError(f"Expected IMAGE tensor [B,H,W,C], got shape {tuple(tensor.shape)}")
    out: list[Image.Image] = []
    count = tensor.shape[0] if max_images is None else min(tensor.shape[0], max_images)
    for idx in range(count):
        arr = tensor[idx].float().clamp(0, 1).numpy()
        arr = (arr * 255.0 + 0.5).astype(np.uint8)
        out.append(Image.fromarray(arr).convert("RGB"))
    return out


def pil_to_jpeg_bytes(image: Image.Image, quality: int = 95) -> bytes:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def pil_to_b64(image: Image.Image, quality: int = 95) -> str:
    return base64.b64encode(pil_to_jpeg_bytes(image, quality)).decode("ascii")


def audio_dict_to_pcm16(audio_input: Any, target_rate: int = 16000) -> bytes:
    if audio_input is None:
        return b""
    sample_rate = 44100
    waveform = audio_input.get("waveform") if isinstance(audio_input, dict) else audio_input
    if isinstance(audio_input, dict):
        sample_rate = int(audio_input.get("sample_rate", 44100))
    if waveform is None:
        return b""

    tensor = waveform.detach().cpu() if torch.is_tensor(waveform) else torch.as_tensor(waveform)
    # ComfyUI normally supplies [B,C,T]. Collapse batch, then channel to mono.
    if tensor.ndim == 3:
        tensor = tensor[0]
    if tensor.ndim == 2:
        tensor = tensor.mean(dim=0)
    tensor = tensor.flatten().float().clamp(-1, 1)

    if sample_rate != target_rate and tensor.numel() > 1:
        try:
            import torchaudio
            tensor = torchaudio.functional.resample(tensor.unsqueeze(0), sample_rate, target_rate).squeeze(0)
        except Exception:
            src_n = tensor.numel()
            new_n = max(1, int(round(src_n * target_rate / sample_rate)))
            nx = np.linspace(0, src_n - 1, new_n)
            tensor = torch.from_numpy(np.interp(nx, np.arange(src_n), tensor.numpy()).astype(np.float32))

    return (tensor.numpy() * 32767.0).astype(np.int16).tobytes()


def pcm16_to_audio(pcm: bytes, sample_rate: int = 24000, channels: int = 1):
    if not pcm:
        return {"waveform": torch.zeros((1, max(1, channels), 1)), "sample_rate": sample_rate}
    arr = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        usable = (len(arr) // channels) * channels
        arr = arr[:usable].reshape(-1, channels).T
    else:
        arr = arr.reshape(1, -1)
    return {"waveform": torch.from_numpy(arr.copy()).unsqueeze(0), "sample_rate": sample_rate}


def extract_response_text(response: Any) -> str:
    try:
        return response.text or ""
    except Exception:
        pass
    try:
        parts = response.candidates[0].content.parts
        return "\n".join(p.text for p in parts if getattr(p, "text", None))
    except Exception:
        return ""


def usage_dict(response: Any) -> dict[str, Any]:
    meta = getattr(response, "usage_metadata", None)
    return {
        "prompt_tokens": int(getattr(meta, "prompt_token_count", 0) or 0),
        "response_tokens": int(getattr(meta, "candidates_token_count", 0) or 0),
        "total_tokens": int(getattr(meta, "total_token_count", 0) or 0),
    }


def interaction_text(interaction: Any) -> str:
    for attr in ("output_text", "text"):
        value = getattr(interaction, attr, None)
        if value:
            return str(value)
    chunks: list[str] = []
    for step in getattr(interaction, "steps", []) or []:
        for block in getattr(step, "content", []) or []:
            if getattr(block, "type", None) == "text" and getattr(block, "text", None):
                chunks.append(block.text)
    return "\n".join(chunks)


def _decode_data(value: Any) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, str):
        return base64.b64decode(value)
    return bytes(value)


def interaction_audio_bytes(interaction: Any) -> tuple[bytes, str]:
    output = getattr(interaction, "output_audio", None)
    if output is not None and getattr(output, "data", None):
        return _decode_data(output.data), str(getattr(output, "mime_type", "audio/wav") or "audio/wav")
    for step in getattr(interaction, "steps", []) or []:
        for block in getattr(step, "content", []) or []:
            if getattr(block, "type", None) == "audio" and getattr(block, "data", None):
                return _decode_data(block.data), str(getattr(block, "mime_type", "audio/wav") or "audio/wav")
    return b"", ""


def interaction_image_bytes(interaction: Any) -> list[bytes]:
    out: list[bytes] = []
    output = getattr(interaction, "output_image", None)
    if output is not None and getattr(output, "data", None):
        out.append(_decode_data(output.data))
    for step in getattr(interaction, "steps", []) or []:
        for block in getattr(step, "content", []) or []:
            if getattr(block, "type", None) == "image" and getattr(block, "data", None):
                out.append(_decode_data(block.data))
    return out


def interaction_video_bytes(interaction: Any) -> bytes | None:
    output = getattr(interaction, "output_video", None)
    if output is not None and getattr(output, "data", None):
        return _decode_data(output.data)
    for step in getattr(interaction, "steps", []) or []:
        for block in getattr(step, "content", []) or []:
            if getattr(block, "type", None) == "video" and getattr(block, "data", None):
                return _decode_data(block.data)
    return None


def save_temp_bytes(data: bytes, suffix: str, prefix: str = "gemini_") -> str:
    try:
        import folder_paths
        temp_root = Path(folder_paths.get_temp_directory())
    except Exception:
        temp_root = Path(os.getenv("TEMP") or os.getenv("TMP") or ".")
    temp_root.mkdir(parents=True, exist_ok=True)
    filename = f"{prefix}{int(time.time() * 1000)}{suffix}"
    path = temp_root / filename
    path.write_bytes(data)
    return str(path)


def decode_video_to_images(video_path: str, *, max_frames: int = 96, fps: float = 12.0) -> torch.Tensor:
    """Decode MP4 to ComfyUI IMAGE batch when ffmpeg/ffprobe are available."""
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        return torch.zeros((1, 512, 512, 3), dtype=torch.float32)

    probe = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", video_path],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        width, height = [int(x) for x in probe.stdout.strip().split(",")[:2]]
    except Exception:
        return torch.zeros((1, 512, 512, 3), dtype=torch.float32)

    command = [
        ffmpeg,
        "-v", "error",
        "-i", video_path,
        "-vf", f"fps={max(1.0, float(fps))}",
        "-frames:v", str(int(max_frames)),
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "pipe:1",
    ]
    proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    raw = proc.stdout
    frame_size = width * height * 3
    if frame_size <= 0 or not raw:
        return torch.zeros((1, 512, 512, 3), dtype=torch.float32)
    count = len(raw) // frame_size
    if count <= 0:
        return torch.zeros((1, 512, 512, 3), dtype=torch.float32)
    raw = raw[: count * frame_size]
    arr = np.frombuffer(raw, dtype=np.uint8).reshape(count, height, width, 3).astype(np.float32) / 255.0
    return torch.from_numpy(arr.copy())
