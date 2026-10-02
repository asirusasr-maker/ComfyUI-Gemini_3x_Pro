"""Gemini/Veo/Omni video generation node — v2.0.

Supports current Google video families:
- Veo 3.1
- Veo 3.1 Fast
- Veo 3.1 Lite
- Gemini Omni 1.1 Flash via Interactions API

The node saves the MP4 into ComfyUI's temp directory and returns a decoded
IMAGE batch plus metadata containing the local video path.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import torch

from .gemini_common import (
    HAS_GENAI,
    VIDEO_MODELS,
    build_client,
    fallback_chain,
    get_api_key,
    decode_video_to_images,
    interaction_video_bytes,
    pil_to_b64,
    run_with_fallback,
    save_temp_bytes,
    tensor_to_pil_list,
)


class GeminiVideoGen:
    VIDEO_MODELS = VIDEO_MODELS
    VEO_CHAIN = [
        "veo-3.1-generate-preview",
        "veo-3.1-fast-generate-preview",
        "veo-3.1-lite-generate-preview",
    ]
    OMNI_CHAIN = [
        "gemini-omni-1.1-flash",
        "veo-3.1-fast-generate-preview",
        "veo-3.1-lite-generate-preview",
    ]
    DURATIONS = ["4s", "6s", "8s", "10s"]
    ASPECT_RATIOS = ["16:9", "9:16"]
    RESOLUTIONS = ["720p", "1080p", "4k"]
    OMNI_TASKS = ["auto", "text_to_video", "image_to_video", "reference_to_video"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": "A cinematic drone shot over a futuristic city"}),
                "model": (cls.VIDEO_MODELS, {"default": "veo-3.1-generate-preview"}),
                "duration": (cls.DURATIONS, {"default": "8s"}),
                "aspect_ratio": (cls.ASPECT_RATIOS, {"default": "16:9"}),
                "resolution": (cls.RESOLUTIONS, {"default": "720p"}),
            },
            "optional": {
                "reference_image": ("IMAGE",),
                "api_key": ("STRING", {"default": ""}),
                "proxy": ("STRING", {"default": ""}),
                "seed": ("INT", {"default": -1, "min": -1, "max": 2147483647}),
                "omni_task": (cls.OMNI_TASKS, {"default": "auto"}),
                "fallback_enabled": ("BOOLEAN", {"default": True}),
                "retries_per_model": ("INT", {"default": 1, "min": 0, "max": 3, "step": 1}),
                "cooldown_seconds": ("FLOAT", {"default": 45.0, "min": 0.0, "max": 300.0, "step": 1.0}),
                "decode_fps": ("FLOAT", {"default": 12.0, "min": 1.0, "max": 24.0, "step": 1.0}),
                "max_frames": ("INT", {"default": 96, "min": 1, "max": 240, "step": 1}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("video_frames", "video_info", "raw_response")
    FUNCTION = "generate_video"
    CATEGORY = "Gemini 3.x"

    @classmethod
    def _candidate_models(cls, selected: str) -> list[str]:
        if selected == "gemini-omni-1.1-flash":
            return fallback_chain(selected, cls.OMNI_CHAIN)
        return fallback_chain(selected, cls.VEO_CHAIN + ["gemini-omni-1.1-flash"])

    @staticmethod
    def _safe_veo_duration(duration: str) -> str:
        seconds = int(str(duration).rstrip("s"))
        # Current Veo 3.1 supports 4/6/8 sec. For a cross-engine fallback from
        # Omni's 10s setting, clamp to the nearest supported Veo length.
        if seconds >= 8:
            return "8"
        if seconds >= 6:
            return "6"
        return "4"

    @staticmethod
    def _safe_veo_resolution(model: str, requested: str) -> str:
        # Keep fallback calls inside each model family's documented envelope.
        if model == "veo-3.1-lite-generate-preview" and requested in {"1080p", "4k"}:
            return "720p"
        if model == "veo-3.1-fast-generate-preview" and requested == "4k":
            return "1080p"
        return requested

    @staticmethod
    def _extract_response_bytes(client, operation) -> tuple[bytes, str]:
        generated = operation.response.generated_videos[0]
        video_obj = generated.video
        # The SDK's recommended download path is used first.
        path = save_temp_bytes(b"", ".mp4", "gemini_video_tmp_")
        try:
            downloaded = None
            try:
                downloaded = client.files.download(file=video_obj, destination=path)
            except TypeError:
                downloaded = client.files.download(file=video_obj, download_path=path)

            if isinstance(downloaded, (bytes, bytearray)):
                data = bytes(downloaded)
                path = save_temp_bytes(data, ".mp4", "gemini_video_")
            elif Path(path).stat().st_size > 0:
                data = Path(path).read_bytes()
            elif getattr(downloaded, "data", None):
                data = downloaded.data if isinstance(downloaded.data, bytes) else bytes(downloaded.data)
                Path(path).write_bytes(data)
            else:
                data = Path(path).read_bytes()

            if not data:
                raise RuntimeError("Veo file download returned an empty MP4.")
            return data, path
        finally:
            # Keep the file; callers need the final local copy. The helper above
            # already created it in ComfyUI temp.
            pass

    def _generate_veo(self, client, model, prompt, reference_image, duration, aspect_ratio, resolution, seed):
        ref = tensor_to_pil_list(reference_image, max_images=1)
        config_kwargs = {
            "aspect_ratio": aspect_ratio,
            "resolution": self._safe_veo_resolution(model, resolution),
            "duration_seconds": self._safe_veo_duration(duration),
            "number_of_videos": 1,
        }
        if seed >= 0:
            config_kwargs["seed"] = int(seed)
        # Some SDK versions may reject duration on specific variants; the retry
        # layer will surface the server/client error. We keep one canonical config.
        import google.genai.types as gtypes
        config = gtypes.GenerateVideosConfig(**config_kwargs)
        kwargs = {"model": model, "prompt": prompt, "config": config}
        if ref:
            kwargs["image"] = ref[0]
        operation = client.models.generate_videos(**kwargs)
        while not operation.done:
            time.sleep(8)
            operation = client.operations.get(operation)
        if not getattr(operation, "response", None) or not operation.response.generated_videos:
            raise RuntimeError("Veo returned no generated video.")
        data, path = self._extract_response_bytes(client, operation)
        return {"data": data, "path": path, "raw": str(operation)}

    def _generate_omni(self, client, prompt, reference_image, aspect_ratio, omni_task):
        input_data = []
        refs = tensor_to_pil_list(reference_image, max_images=1)
        if refs:
            input_data.append({
                "type": "image",
                "data": pil_to_b64(refs[0]),
                "mime_type": "image/jpeg",
            })
        text = prompt
        if aspect_ratio:
            text += f" Generate the video in {aspect_ratio} format."
        input_data.append({"type": "text", "text": text})

        generation_config = {"video_config": {}}
        if omni_task != "auto":
            generation_config["video_config"]["task"] = omni_task

        interaction = client.interactions.create(
            model="gemini-omni-1.1-flash",
            input=input_data,
            generation_config=generation_config,
        )
        data = interaction_video_bytes(interaction)
        if not data:
            raise RuntimeError("Gemini Omni returned no video data.")
        return {"data": data, "path": save_temp_bytes(data, ".mp4", "gemini_omni_"), "raw": str(interaction)}

    def generate_video(
        self,
        prompt,
        model,
        duration,
        aspect_ratio,
        resolution="720p",
        reference_image=None,
        api_key="",
        proxy="",
        seed=-1,
        omni_task="auto",
        fallback_enabled=True,
        retries_per_model=1,
        cooldown_seconds=45.0,
        decode_fps=12.0,
        max_frames=96,
    ):
        placeholder = torch.zeros((1, 512, 512, 3), dtype=torch.float32)
        if not HAS_GENAI:
            return placeholder, "Error: google-genai is not installed", ""
        key = get_api_key(api_key)
        if not key:
            return placeholder, "Error: No Gemini API key", ""
        try:
            client = build_client(key, proxy)
        except Exception as exc:
            return placeholder, f"Error initializing Gemini client: {exc}", ""

        candidates = self._candidate_models(model)

        def request(current_model):
            if current_model == "gemini-omni-1.1-flash":
                return self._generate_omni(client, prompt, reference_image, aspect_ratio, omni_task)
            return self._generate_veo(client, current_model, prompt, reference_image, duration, aspect_ratio, resolution, seed)

        try:
            result, actual_model, fallback_used = run_with_fallback(
                candidates,
                request,
                retries_per_model=retries_per_model,
                cooldown_seconds=cooldown_seconds,
                fallback_enabled=fallback_enabled,
                log_prefix="[Gemini Video Gen]",
            )
        except Exception as exc:
            return placeholder, f"Error: {exc}", ""

        path = result["path"]
        frames = decode_video_to_images(path, max_frames=int(max_frames), fps=float(decode_fps))
        effective_duration = self._safe_veo_duration(duration) if actual_model.startswith("veo-") else None
        effective_resolution = self._safe_veo_resolution(actual_model, resolution) if actual_model.startswith("veo-") else None
        info = {
            "requested_model": model,
            "actual_model": actual_model,
            "fallback_used": fallback_used,
            "duration_requested": duration,
            "effective_duration_seconds": effective_duration,
            "aspect_ratio": aspect_ratio,
            "resolution_requested": resolution,
            "effective_resolution": effective_resolution,
            "video_path": path,
            "decode_fps": decode_fps,
            "decoded_frames": int(frames.shape[0]),
            "status": "generated",
        }
        return frames, json.dumps(info, ensure_ascii=False, indent=2), result["raw"]
