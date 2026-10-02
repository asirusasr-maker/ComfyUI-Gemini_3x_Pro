"""Gemini 3.x Pro Multimodal Node — v2.0.

Adds:
- current Gemini 3.x model list
- bounded retry with automatic model fallback
- temporary per-model cooldown after repeated 429/5xx failures
- AFC explicitly disabled
- persistent chat mode with stable session IDs
- structured JSON output
- optional Google Search grounding
- multimodal text/image/audio/video-frame inputs
"""
from __future__ import annotations

import json
from typing import Any

from PIL import Image as PILImage

try:
    from google.genai import types
except Exception:
    types = None  # type: ignore[assignment]

from .gemini_common import (
    HAS_GENAI,
    FLASH_MODELS,
    PRO_MODEL,
    build_client,
    fallback_chain,
    get_api_key,
    make_generate_config,
    run_with_fallback,
    tensor_to_pil_list,
    usage_dict,
)


class Gemini3xPro:
    MODELS = FLASH_MODELS + [PRO_MODEL]
    FALLBACK_CHAIN = FLASH_MODELS

    _chat_history: dict[str, list[Any]] = {}

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": "Analyze this content"}),
                "model": (cls.MODELS, {"default": "gemini-3.8-flash"}),
                "operation_mode": (["analysis", "chat", "structured_json"], {"default": "analysis"}),
            },
            "optional": {
                "images": ("IMAGE",),
                "video": ("IMAGE",),
                "audio": ("AUDIO",),
                "system_instruction": ("STRING", {"multiline": True, "default": ""}),
                "api_key": ("STRING", {"default": "", "multiline": False}),
                "proxy": ("STRING", {"default": "", "multiline": False}),
                "temperature": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 1.0, "step": 0.05}),
                "max_output_tokens": ("INT", {"default": 8192, "min": 1, "max": 65536, "step": 1}),
                "top_p": ("FLOAT", {"default": 0.95, "min": 0.0, "max": 1.0, "step": 0.01}),
                "top_k": ("INT", {"default": 40, "min": 1, "max": 100, "step": 1}),
                "use_search_grounding": ("BOOLEAN", {"default": False}),
                "chat_mode": ("BOOLEAN", {"default": False}),
                "chat_session": ("STRING", {"default": "default", "multiline": False}),
                "clear_history": ("BOOLEAN", {"default": False}),
                "fallback_enabled": ("BOOLEAN", {"default": True}),
                "retries_per_model": ("INT", {"default": 1, "min": 0, "max": 4, "step": 1}),
                "cooldown_seconds": ("FLOAT", {"default": 30.0, "min": 0.0, "max": 300.0, "step": 1.0}),
                "json_schema": ("STRING", {"multiline": True, "default": ""}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("generated_content", "raw_response", "usage_info")
    FUNCTION = "generate"
    CATEGORY = "Gemini 3.x"
    OUTPUT_NODE = False

    @staticmethod
    def _parts_for_chat(items: list[Any]) -> list[Any]:
        parts = []
        for item in items:
            if isinstance(item, str):
                parts.append(types.Part(text=item))
            elif isinstance(item, PILImage.Image):
                parts.append(types.Part.from_image(item))
            elif isinstance(item, types.Part):
                parts.append(item)
        return parts

    @staticmethod
    def _build_contents(prompt, images=None, video=None, audio=None):
        from .gemini_common import audio_dict_to_pcm16
        contents: list[Any] = []

        for img in tensor_to_pil_list(images):
            contents.append(img)

        # Gemini Flash accepts actual video input, but ComfyUI passes VIDEO here
        # as an IMAGE tensor. We preserve compatibility by sending sampled frames.
        for frame in tensor_to_pil_list(video, max_images=16):
            contents.append(frame)

        if audio is not None:
            pcm = audio_dict_to_pcm16(audio, target_rate=16000)
            if pcm:
                contents.append(types.Part.from_bytes(data=pcm, mime_type="audio/pcm;rate=16000"))

        if prompt:
            contents.append(prompt)
        return contents

    @classmethod
    def _candidate_models(cls, selected: str) -> list[str]:
        if selected == PRO_MODEL:
            # Pro is preview; if temporarily unavailable, move into the current
            # stable Flash family in descending capability order.
            return [PRO_MODEL] + cls.FALLBACK_CHAIN
        return fallback_chain(selected, cls.FALLBACK_CHAIN)

    def _make_config(
        self,
        *,
        temperature,
        max_output_tokens,
        top_p,
        top_k,
        system_instruction,
        use_search_grounding,
        structured_schema=None,
    ):
        return make_generate_config(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            top_p=top_p,
            top_k=top_k,
            system_instruction=system_instruction,
            use_search_grounding=use_search_grounding,
            response_mime_type="application/json" if structured_schema is not None else None,
            response_schema=structured_schema,
        )

    def generate(
        self,
        prompt,
        model,
        operation_mode,
        images=None,
        video=None,
        audio=None,
        system_instruction="",
        api_key="",
        proxy="",
        temperature=0.7,
        max_output_tokens=8192,
        top_p=0.95,
        top_k=40,
        use_search_grounding=False,
        chat_mode=False,
        chat_session="default",
        clear_history=False,
        fallback_enabled=True,
        retries_per_model=1,
        cooldown_seconds=30.0,
        json_schema="",
    ):
        if not HAS_GENAI:
            return ("Error: google-genai is not installed", "", "")

        key = get_api_key(api_key)
        if not key:
            return ("Error: No Gemini API key. Put it in config.json, GEMINI_API_KEY, or the node input.", "", "")

        try:
            client = build_client(key, proxy)
        except Exception as exc:
            return (f"Error initializing Gemini client: {exc}", "", "")
        if client is None:
            return ("Error: Failed to initialize Gemini client", "", "")

        contents = self._build_contents(prompt, images, video, audio)
        if not contents:
            return ("Error: No content provided", "", "")

        schema = None
        if operation_mode == "structured_json" and json_schema.strip():
            try:
                schema = json.loads(json_schema)
            except json.JSONDecodeError as exc:
                return (f"Error: Invalid JSON schema: {exc}", "", "")

        config = self._make_config(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            top_p=top_p,
            top_k=top_k,
            system_instruction=system_instruction,
            use_search_grounding=use_search_grounding,
            structured_schema=schema,
        )

        selected_candidates = self._candidate_models(model)
        session_id = None
        fallback_used = False
        actual_model = model
        response = None

        if chat_mode or operation_mode == "chat":
            session_id = f"{chat_session.strip() or 'default'}::{model}"
            if clear_history or session_id not in self._chat_history:
                self._chat_history[session_id] = []
            user_parts = self._parts_for_chat(contents)
            self._chat_history[session_id].append(
                types.Content(role="user", parts=user_parts)
            )

            def do_chat(current_model):
                chat = client.chats.create(
                    model=current_model,
                    history=self._chat_history[session_id][:-1],
                )
                return chat.send_message(user_parts, config=config)

            try:
                response, actual_model, fallback_used = run_with_fallback(
                    selected_candidates,
                    do_chat,
                    retries_per_model=retries_per_model,
                    cooldown_seconds=cooldown_seconds,
                    fallback_enabled=fallback_enabled,
                    log_prefix="[Gemini 3.x Pro]",
                )
            except Exception as exc:
                # Do not poison the history with a turn Gemini never answered.
                self._chat_history[session_id].pop()
                raise

            text = getattr(response, "text", "") or str(response)
            self._chat_history[session_id].append(
                types.Content(role="model", parts=[types.Part(text=text)])
            )
        else:
            def do_generate(current_model):
                return client.models.generate_content(
                    model=current_model,
                    contents=contents,
                    config=config,
                )

            response, actual_model, fallback_used = run_with_fallback(
                selected_candidates,
                do_generate,
                retries_per_model=retries_per_model,
                cooldown_seconds=cooldown_seconds,
                fallback_enabled=fallback_enabled,
                log_prefix="[Gemini 3.x Pro]",
            )

        generated_text = getattr(response, "text", "") or str(response)
        usage = usage_dict(response)
        raw_info = {
            "requested_model": model,
            "actual_model": actual_model,
            "fallback_used": fallback_used,
            "operation_mode": operation_mode,
            "chat_mode": bool(chat_mode or operation_mode == "chat"),
            "session_id": session_id,
            "history_length": len(self._chat_history.get(session_id, [])) if session_id else 0,
            "search_grounding": bool(use_search_grounding),
            **usage,
        }
        return generated_text, str(response), json.dumps(raw_info, indent=2, ensure_ascii=False)
