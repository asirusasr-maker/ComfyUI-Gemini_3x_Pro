"""Gemini native image generation node — current Nano Banana family."""
from __future__ import annotations

import io
import json

import numpy as np
import torch
from PIL import Image

from .gemini_common import (
    HAS_GENAI,
    IMAGE_MODELS,
    build_client,
    fallback_chain,
    get_api_key,
    interaction_image_bytes,
    interaction_text,
    pil_to_b64,
    run_with_fallback,
    tensor_to_pil_list,
)


class GeminiImageGen:
    # User-facing names match the current Google/Nano Banana branding.
    # Values are mapped to the official Gemini API model IDs before calling the API.
    MODEL_LABEL_TO_ID = {
        "Nano Banana Pro": "gemini-3-pro-image",
        "Nano Banana 2": "gemini-3.1-flash-image",
        "Nano Banana 2 Lite": "gemini-3.1-flash-lite-image",
    }
    MODEL_ID_TO_LABEL = {v: k for k, v in MODEL_LABEL_TO_ID.items()}
    IMAGE_MODELS = list(MODEL_LABEL_TO_ID.keys())
    ASPECT_RATIOS = [
        "1:1", "3:2", "2:3", "3:4", "4:3", "4:5", "5:4",
        "9:16", "16:9", "21:9"
    ]
    FALLBACK_CHAIN = [
        "gemini-3-pro-image",
        "gemini-3.1-flash-image",
        "gemini-3.1-flash-lite-image",
    ]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": "A cinematic portrait"}),
                "model": (cls.IMAGE_MODELS, {"default": "Nano Banana 2"}),
                "aspect_ratio": (cls.ASPECT_RATIOS, {"default": "1:1"}),
            },
            "optional": {
                "reference_image": ("IMAGE",),
                "negative_prompt": ("STRING", {"multiline": True, "default": ""}),
                "api_key": ("STRING", {"default": ""}),
                "proxy": ("STRING", {"default": ""}),
                "num_images": ("INT", {"default": 1, "min": 1, "max": 4, "step": 1}),
                "fallback_enabled": ("BOOLEAN", {"default": True}),
                "retries_per_model": ("INT", {"default": 1, "min": 0, "max": 4, "step": 1}),
                "cooldown_seconds": ("FLOAT", {"default": 30.0, "min": 0.0, "max": 300.0, "step": 1.0}),
                "image_size": (["1K", "2K", "4K"], {"default": "1K"}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("generated_images", "generation_info", "raw_response")
    FUNCTION = "generate_image"
    CATEGORY = "Gemini 3.x"

    @staticmethod
    def _candidate_models(selected: str) -> list[str]:
        selected_id = GeminiImageGen.MODEL_LABEL_TO_ID.get(selected, selected)
        return fallback_chain(selected_id, GeminiImageGen.FALLBACK_CHAIN)

    @staticmethod
    def _reference_input(reference_image):
        imgs = tensor_to_pil_list(reference_image, max_images=4)
        return imgs[0] if imgs else None

    @staticmethod
    def _build_input(prompt: str, negative_prompt: str, reference_image):
        blocks = []
        ref = GeminiImageGen._reference_input(reference_image)
        if ref is not None:
            blocks.append({
                "type": "image",
                "mime_type": "image/jpeg",
                "data": pil_to_b64(ref),
            })
        text = prompt.strip()
        if negative_prompt.strip():
            text += f"\nAvoid: {negative_prompt.strip()}"
        blocks.append({"type": "text", "text": text})
        return blocks

    @staticmethod
    def _safe_image_size(model: str, requested: str) -> str:
        # Lite has a smaller output ceiling than Pro/Flash; avoid an otherwise
        # avoidable 400 when fallback lands on Lite.
        if model == "gemini-3.1-flash-lite-image":
            return "1K"
        return requested

    @staticmethod
    def _extract_images(interaction):
        out = []
        for data in interaction_image_bytes(interaction):
            try:
                out.append(Image.open(io.BytesIO(data)).convert("RGB"))
            except Exception:
                pass
        return out

    def generate_image(
        self,
        prompt,
        model,
        aspect_ratio,
        reference_image=None,
        negative_prompt="",
        api_key="",
        proxy="",
        num_images=1,
        fallback_enabled=True,
        retries_per_model=1,
        cooldown_seconds=30.0,
        image_size="1K",
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

        input_data = self._build_input(prompt, negative_prompt, reference_image)
        all_images = []
        raw_responses = []
        actual_models = []
        effective_sizes = []

        for image_idx in range(max(1, int(num_images))):
            def do_request(current_model):
                effective_size = self._safe_image_size(current_model, image_size)
                return client.interactions.create(
                    model=current_model,
                    input=input_data,
                    response_format={
                        "type": "image",
                        "mime_type": "image/jpeg",
                        "aspect_ratio": aspect_ratio,
                        "image_size": effective_size,
                    },
                )

            try:
                interaction, actual_model, fallback_used = run_with_fallback(
                    self._candidate_models(model),
                    do_request,
                    retries_per_model=retries_per_model,
                    cooldown_seconds=cooldown_seconds,
                    fallback_enabled=fallback_enabled,
                    log_prefix="[Gemini Image Gen]",
                )
            except Exception as exc:
                if not all_images:
                    return placeholder, f"Error: {exc}", ""
                break

            imgs = self._extract_images(interaction)
            if not imgs:
                text = interaction_text(interaction)
                if not all_images:
                    return placeholder, f"No image returned. Response: {text}", str(interaction)
                continue
            all_images.extend(imgs)
            raw_responses.append(str(interaction))
            actual_models.append((actual_model, fallback_used))
            effective_sizes.append(self._safe_image_size(actual_model, image_size))

        if not all_images:
            return placeholder, "No images generated.", "\n".join(raw_responses)

        tensors = []
        for img in all_images:
            arr = np.asarray(img).astype(np.float32) / 255.0
            tensors.append(torch.from_numpy(arr.copy()))
        batch = torch.stack(tensors)

        info = {
            "requested_model": model,
            "requested_model_id": self.MODEL_LABEL_TO_ID.get(model, model),
            "actual_models": [m for m, _ in actual_models],
            "actual_model_labels": [self.MODEL_ID_TO_LABEL.get(m, m) for m, _ in actual_models],

            "fallback_used": any(flag for _, flag in actual_models),
            "aspect_ratio": aspect_ratio,
            "image_size_requested": image_size,
            "effective_image_sizes": effective_sizes,
            "num_images_requested": int(num_images),
            "num_images_returned": len(all_images),
            "prompt": prompt,
        }
        return batch, json.dumps(info, ensure_ascii=False, indent=2), "\n".join(raw_responses)
