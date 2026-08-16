"""
Gemini Image Generation Node
Uses Google Interactions API for Nano Banana image generation
"""

import os
import json
import io
import base64
import torch
import numpy as np
from PIL import Image

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


class GeminiImageGen:
    CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

    IMAGE_MODELS = [
        "gemini-3.1-flash-image",
        "gemini-3-pro-image",
        "gemini-3.1-flash-lite-image",
    ]

    ASPECT_RATIOS = ["1:1", "16:9", "9:16", "4:3", "3:4", "21:9"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": "A beautiful landscape"}),
                "model": (cls.IMAGE_MODELS, {"default": "gemini-3.1-flash-image"}),
                "aspect_ratio": (cls.ASPECT_RATIOS, {"default": "1:1"}),
            },
            "optional": {
                "reference_image": ("IMAGE",),
                "negative_prompt": ("STRING", {"multiline": True, "default": ""}),
                "api_key": ("STRING", {"default": ""}),
                "proxy": ("STRING", {"default": ""}),
                "seed": ("INT", {"default": -1, "min": -1, "max": 2147483647}),
                "num_images": ("INT", {"default": 1, "min": 1, "max": 4, "step": 1}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("generated_images", "generation_info", "raw_response")
    FUNCTION = "generate_image"
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

    def _pil_to_base64(self, pil_img):
        buffer = io.BytesIO()
        pil_img = pil_img.convert("RGB")
        pil_img.save(buffer, format="JPEG", quality=95)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def generate_image(self, prompt, model, aspect_ratio, reference_image=None,
                       negative_prompt="", api_key="", proxy="", seed=-1, num_images=1):

        if not HAS_GENAI:
            placeholder = torch.zeros((1, 512, 512, 3))
            return (placeholder, "Error: google-genai not installed", "")

        key = self._get_api_key(api_key)
        if not key:
            placeholder = torch.zeros((1, 512, 512, 3))
            return (placeholder, "Error: No API key", "")

        client = genai.Client(api_key=key)

        # Build input for interactions API
        input_data = []

        # Add reference image if provided
        ref_img = self._tensor_to_pil(reference_image)
        if ref_img:
            input_data.append({
                "type": "image",
                "mime_type": "image/jpeg",
                "data": self._pil_to_base64(ref_img)
            })

        # Build prompt text
        full_prompt = prompt
        if negative_prompt:
            full_prompt += f" Avoid: {negative_prompt}"

        input_data.append({"type": "text", "text": full_prompt})

        try:
            # Use interactions API for image generation
            interaction = client.interactions.create(
                model=model,
                input=input_data,
                response_format={
                    "type": "image",
                    "mime_type": "image/jpeg",
                    "aspect_ratio": aspect_ratio,
                }
            )

            # Extract generated image
            images = []
            output_text = ""

            for step in interaction.steps:
                if step.type == "model_output":
                    for content_block in step.content:
                        if content_block.type == "text":
                            output_text += content_block.text + "\n"
                        elif content_block.type == "image":
                            img_bytes = base64.b64decode(content_block.data)
                            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                            img_np = np.array(img).astype(np.float32) / 255.0
                            images.append(torch.from_numpy(img_np))

            # Fallback: try output_image property
            if not images and hasattr(interaction, 'output_image') and interaction.output_image:
                img_bytes = base64.b64decode(interaction.output_image.data)
                img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                img_np = np.array(img).astype(np.float32) / 255.0
                images.append(torch.from_numpy(img_np))

            if not images:
                placeholder = torch.zeros((1, 512, 512, 3))
                return (placeholder, "No images generated. Response text: " + output_text, str(interaction))

            output_tensor = torch.stack(images)

            info = {
                "model": model,
                "aspect_ratio": aspect_ratio,
                "num_images": len(images),
                "prompt": prompt,
                "response_text": output_text.strip(),
            }

            return (output_tensor, json.dumps(info, ensure_ascii=False), str(interaction))

        except Exception as e:
            error_msg = str(e)
            print(f"[Gemini Image Gen] Error: {error_msg}")
            placeholder = torch.zeros((1, 512, 512, 3))
            return (placeholder, f"Error: {error_msg}", "")
