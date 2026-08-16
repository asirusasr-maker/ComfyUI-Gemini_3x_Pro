"""
Gemini Live Audio Chat Node
"""

import os
import json
import torch
import numpy as np

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


class GeminiAudioChat:
    CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text_input": ("STRING", {"multiline": True, "default": "Hello!"}),
                "system_prompt": ("STRING", {"multiline": True, "default": "You are a helpful assistant."}),
            },
            "optional": {
                "audio_input": ("AUDIO",),
                "api_key": ("STRING", {"default": ""}),
                "proxy": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("AUDIO", "STRING", "STRING")
    RETURN_NAMES = ("audio_output", "text_response", "session_info")
    FUNCTION = "chat"
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

    def _audio_to_bytes(self, audio_tensor, sample_rate=24000):
        if audio_tensor is None:
            return None
        audio_np = audio_tensor.cpu().numpy().squeeze()
        audio_int16 = (audio_np * 32767).astype(np.int16)
        return audio_int16.tobytes()

    def chat(self, text_input, system_prompt, audio_input=None, api_key="", proxy=""):

        if not HAS_GENAI:
            return (None, "Error: google-genai not installed", "")

        key = self._get_api_key(api_key)
        if not key:
            return (None, "Error: No API key", "")

        info = {
            "model": "gemini-3.1-flash-live-preview",
            "note": "Live API requires async streaming. This is a simplified version.",
            "system_prompt": system_prompt,
            "text_input": text_input,
        }

        placeholder_audio = torch.zeros((1, 24000))
        return (placeholder_audio, "Live audio chat placeholder. Use Live API for real-time.", json.dumps(info, ensure_ascii=False))
