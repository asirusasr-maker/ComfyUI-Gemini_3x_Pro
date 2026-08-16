"""
Gemini 3.x Pro Multimodal Node
Fixed Chat Mode for google-genai 2.x
Fixed AUDIO dict handling + audio as types.Part
"""

import os
import json
import io
import torch
import numpy as np
from PIL import Image

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False
    print("[Gemini 3.x Pro] Warning: google-genai not installed")


class Gemini3xPro:
    CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

    MODELS = [
        "gemini-3.7-flash",
        "gemini-3.6-flash", 
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.1-pro",
        "gemini-3.1-flash-live-preview",
        "gemini-flash-latest",
        "gemini-pro-latest",
    ]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": "Analyze this content"}),
                "model": (cls.MODELS, {"default": "gemini-3.7-flash"}),
                "operation_mode": (["analysis", "chat", "structured_json"], {"default": "analysis"}),
            },
            "optional": {
                "images": ("IMAGE",),
                "video": ("IMAGE",),
                "audio": ("AUDIO",),
                "system_instruction": ("STRING", {"multiline": True, "default": ""}),
                "api_key": ("STRING", {"default": ""}),
                "proxy": ("STRING", {"default": ""}),
                "temperature": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 2.0, "step": 0.1}),
                "max_output_tokens": ("INT", {"default": 8192, "min": 1, "max": 65536, "step": 1}),
                "top_p": ("FLOAT", {"default": 0.95, "min": 0.0, "max": 1.0, "step": 0.01}),
                "top_k": ("INT", {"default": 40, "min": 1, "max": 100, "step": 1}),
                "use_search_grounding": ("BOOLEAN", {"default": False}),
                "chat_mode": ("BOOLEAN", {"default": False}),
                "clear_history": ("BOOLEAN", {"default": False}),
                "json_schema": ("STRING", {"multiline": True, "default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("generated_content", "raw_response", "usage_info")
    FUNCTION = "generate"
    CATEGORY = "Gemini 3.x"
    OUTPUT_NODE = False

    _chat_history = {}

    def __init__(self):
        self.client = None
        self.current_model = None

    def _get_api_key(self, api_key_input):
        if api_key_input and api_key_input.strip():
            return api_key_input.strip()
        if os.path.exists(self.CONFIG_PATH):
            try:
                with open(self.CONFIG_PATH, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    key = config.get("GEMINI_API_KEY", "")
                    if key:
                        return key
            except Exception:
                pass
        return os.environ.get("GEMINI_API_KEY", "")

    def _init_client(self, api_key, proxy=""):
        if not HAS_GENAI:
            return None
        kwargs = {"api_key": api_key}
        if proxy:
            kwargs["http_options"] = {"api_version": "v1beta", "base_url": proxy}
        try:
            return genai.Client(**kwargs)
        except Exception as e:
            print(f"[Gemini 3.x Pro] Client init error: {e}")
            return None

    def _tensor_to_pil(self, image_tensor):
        if image_tensor is None:
            return None
        if len(image_tensor.shape) == 4:
            images = []
            for i in range(image_tensor.shape[0]):
                img = image_tensor[i].cpu().numpy()
                img = (img * 255).astype(np.uint8)
                images.append(Image.fromarray(img))
            return images
        else:
            img = image_tensor.cpu().numpy()
            img = (img * 255).astype(np.uint8)
            return [Image.fromarray(img)]

    def _audio_to_bytes(self, audio_input):
        """Convert ComfyUI AUDIO dict to WAV bytes."""
        if audio_input is None:
            return None

        if isinstance(audio_input, dict) and "waveform" in audio_input:
            audio_tensor = audio_input["waveform"]
            sr = audio_input.get("sample_rate", 44100)
        else:
            audio_tensor = audio_input
            sr = 44100

        audio_np = audio_tensor.cpu().numpy()
        if len(audio_np.shape) > 1:
            audio_np = audio_np.squeeze()
        audio_int16 = (audio_np * 32767).astype(np.int16)

        import wave
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sr)
            wav_file.writeframes(audio_int16.tobytes())
        return buffer.getvalue()

    def _build_contents(self, prompt, images=None, video=None, audio=None):
        """Build contents list for generate_content.
        Returns list of: str, PIL.Image, or types.Part (for audio)"""
        contents = []
        if images is not None:
            pil_images = self._tensor_to_pil(images)
            for pil_img in pil_images:
                contents.append(pil_img)
        if video is not None:
            pil_frames = self._tensor_to_pil(video)
            for i, frame in enumerate(pil_frames[:16]):
                contents.append(frame)
        if audio is not None:
            audio_bytes = self._audio_to_bytes(audio)
            if audio_bytes:
                contents.append(types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"))
        if prompt:
            contents.append(prompt)
        return contents

    def _items_to_parts(self, items):
        """Convert content items to list of types.Part for chat API."""
        parts = []
        for item in items:
            if isinstance(item, str):
                parts.append(types.Part(text=item))
            elif isinstance(item, Image.Image):
                parts.append(types.Part.from_image(item))
            elif isinstance(item, types.Part):
                parts.append(item)
        return parts

    def generate(self, prompt, model, operation_mode, images=None, video=None, 
                 audio=None, system_instruction="", api_key="", proxy="",
                 temperature=0.7, max_output_tokens=8192, top_p=0.95, top_k=40,
                 use_search_grounding=False, chat_mode=False, clear_history=False,
                 json_schema=""):

        if not HAS_GENAI:
            return ("Error: google-genai not installed", "", "")

        key = self._get_api_key(api_key)
        if not key:
            return ("Error: No API key", "", "")

        client = self._init_client(key, proxy)
        if client is None:
            return ("Error: Failed to initialize Gemini client", "", "")

        contents = self._build_contents(prompt, images, video, audio)
        if not contents:
            return ("Error: No content provided", "", "")

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            top_p=top_p,
            top_k=top_k,
        )

        if system_instruction:
            config.system_instruction = system_instruction

        if use_search_grounding:
            config.tools = [types.Tool(google_search=types.GoogleSearch())]

        if operation_mode == "structured_json" and json_schema:
            try:
                schema_dict = json.loads(json_schema)
                config.response_mime_type = "application/json"
                config.response_schema = schema_dict
            except json.JSONDecodeError:
                return ("Error: Invalid JSON schema", "", "")

        session_id = None

        if chat_mode:
            session_id = f"{model}_chat_session"

            if clear_history or session_id not in self._chat_history:
                self._chat_history[session_id] = []
                if system_instruction:
                    self._chat_history[session_id].append(
                        types.Content(role="user", parts=[types.Part(text=system_instruction)])
                    )

            user_parts = self._items_to_parts(contents)

            self._chat_history[session_id].append(
                types.Content(role="user", parts=user_parts)
            )

            chat = client.chats.create(
                model=model, 
                history=self._chat_history[session_id][:-1]
            )

            response = chat.send_message(user_parts, config=config)

            self._chat_history[session_id].append(
                types.Content(role="model", parts=[types.Part(text=response.text)])
            )
        else:
            response = client.models.generate_content(
                model=model, 
                contents=contents, 
                config=config
            )

        try:
            generated_text = response.text
        except Exception:
            generated_text = str(response)

        raw_info = {
            "model": model,
            "operation_mode": operation_mode,
            "chat_mode": chat_mode,
            "session_id": session_id,
            "history_length": len(self._chat_history.get(session_id, [])) if session_id else 0,
            "prompt_tokens": response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
            "response_tokens": response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
            "total_tokens": response.usage_metadata.total_token_count if response.usage_metadata else 0,
        }

        usage_str = json.dumps(raw_info, indent=2, ensure_ascii=False)
        return (generated_text, str(response), usage_str)
