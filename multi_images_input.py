"""
Multi Images Input Node
"""

import torch
import torch.nn.functional as F


class MultiImagesInput:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "inputcount": ("INT", {"default": 4, "min": 1, "max": 16, "step": 1}),
            },
            "optional": {
                "image_1": ("IMAGE",),
                "image_2": ("IMAGE",),
                "image_3": ("IMAGE",),
                "image_4": ("IMAGE",),
                "image_5": ("IMAGE",),
                "image_6": ("IMAGE",),
                "image_7": ("IMAGE",),
                "image_8": ("IMAGE",),
                "image_9": ("IMAGE",),
                "image_10": ("IMAGE",),
                "image_11": ("IMAGE",),
                "image_12": ("IMAGE",),
                "image_13": ("IMAGE",),
                "image_14": ("IMAGE",),
                "image_15": ("IMAGE",),
                "image_16": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "combine"
    CATEGORY = "Gemini 3.x"

    def combine(self, inputcount=4, **kwargs):
        images = []
        for i in range(1, inputcount + 1):
            key = f"image_{i}"
            if key in kwargs and kwargs[key] is not None:
                img = kwargs[key]
                if len(img.shape) == 3:
                    images.append(img)
                elif len(img.shape) == 4:
                    for j in range(img.shape[0]):
                        images.append(img[j])

        if not images:
            return (torch.zeros((1, 512, 512, 3)),)

        target_h, target_w = images[0].shape[0], images[0].shape[1]
        resized = []
        for img in images:
            if img.shape[0] != target_h or img.shape[1] != target_w:
                img = img.permute(2, 0, 1).unsqueeze(0)
                img = F.interpolate(img, size=(target_h, target_w), mode='bilinear', align_corners=False)
                img = img.squeeze(0).permute(1, 2, 0)
            resized.append(img)

        batch = torch.stack(resized)
        return (batch,)
