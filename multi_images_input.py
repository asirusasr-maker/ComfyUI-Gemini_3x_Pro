"""Multi-image batch input helper for Gemini nodes."""
from __future__ import annotations

import torch
import torch.nn.functional as F


class MultiImagesInput:
    @classmethod
    def INPUT_TYPES(cls):
        optional = {f"image_{i}": ("IMAGE",) for i in range(1, 17)}
        return {
            "required": {
                "inputcount": ("INT", {"default": 4, "min": 1, "max": 16, "step": 1}),
            },
            "optional": optional,
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "combine"
    CATEGORY = "Gemini 3.x"

    def combine(self, inputcount=4, **kwargs):
        images = []
        for i in range(1, int(inputcount) + 1):
            img = kwargs.get(f"image_{i}")
            if img is None:
                continue
            if img.ndim == 3:
                images.append(img)
            elif img.ndim == 4:
                images.extend([img[j] for j in range(img.shape[0])])

        if not images:
            return (torch.zeros((1, 512, 512, 3), dtype=torch.float32),)

        target_h, target_w = images[0].shape[:2]
        normalized = []
        for img in images:
            if img.shape[0] != target_h or img.shape[1] != target_w:
                chw = img.permute(2, 0, 1).unsqueeze(0).float()
                chw = F.interpolate(chw, size=(target_h, target_w), mode="bilinear", align_corners=False)
                img = chw.squeeze(0).permute(1, 2, 0)
            normalized.append(img.float().clamp(0, 1))
        return (torch.stack(normalized),)
