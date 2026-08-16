"""
Gemini Video Generation Node
"""

import os
import json
import torch
import numpy as np
from PIL import Image

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


class GeminiVideoGen:
    CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

    VIDEO_MODELS = [
        "veo-3.1-generate-preview",
        "veo-3.1-lite-generate-preview",
        "gemini-omni-flash",
    ]

    DURATIONS = ["3s", "5s", "8s", "10s"]
    ASPECT_RATIOS = ["16:9", "9:16", "1:1"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": "A cinematic drone shot"}),
                "model": (cls.VIDEO_MODELS, {"default": "veo-3.1-generate-preview"}),
                "duration": (cls.DURATIONS, {"default": "5s"}),
                "aspect_ratio": (cls.ASPECT_RATIOS, {"default": "16:9"}),
            },
            "optional": {
                "reference_image": ("IMAGE",),
                "api_key": ("STRING", {"default": ""}),
                "proxy": ("STRING", {"default": ""}),
                "seed": ("INT", {"default": -1, "min": -1, "max": 2147483647}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("video_frames", "video_info", "raw_response")
    FUNCTION = "generate_video"
    CATEGORY = "Gemini 3.x"

    def _get_api_key(self, api_key_input):
        if api_key_input and api_key_input.strip():
            return api_key_input.strip()
        if os.path.exists(self.CONFIG_PATH):
            try:
                with open(self.CONFIG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f).get("GEMINI_API_KEY", "")
            except Exception:
                pass
        return os.environ.get("GEMINI_API_KEY", "")

    def _tensor_to_pil(self, image_tensor):
        if image_tensor is None:
            return None
        if len(image_tensor.shape) == 4:
            img = image_tensor[0].cpu().numpy()
        else:
            img = image_tensor.cpu().numpy()
        img = (img * 255).astype(np.uint8)
        return Image.fromarray(img)

    def generate_video(self, prompt, model, duration, aspect_ratio,
                       reference_image=None, api_key="", proxy="", seed=-1):

        if not HAS_GENAI:
            return (None, "Error: google-genai not installed", "")

        key = self._get_api_key(api_key)
        if not key:
            return (None, "Error: No API key", "")

        client = genai.Client(api_key=key)
        contents = [prompt]

        ref_img = self._tensor_to_pil(reference_image)
        if ref_img:
            contents.insert(0, ref_img)

        try:
            operation = client.models.generate_videos(
                model=model,
                contents=contents,
                config=types.GenerateVideosConfig(aspect_ratio=aspect_ratio, number_of_videos=1)
            )
            result = operation.result()

            info = {
                "model": model,
                "duration": duration,
                "aspect_ratio": aspect_ratio,
                "prompt": prompt,
                "status": "generated"
            }

            placeholder = torch.zeros((1, 512, 512, 3))
            return (placeholder, json.dumps(info, ensure_ascii=False), str(result))

        except Exception as e:
            return (None, f"Error: {str(e)}", "")
