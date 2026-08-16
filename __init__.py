"""
ComfyUI-Gemini_3x_Pro
Advanced Gemini 3.x nodes for ComfyUI
"""

from .gemini_3x_node import Gemini3xPro
from .gemini_image_gen_node import GeminiImageGen
from .gemini_video_node import GeminiVideoGen
from .gemini_tts_node import GeminiTTS
from .gemini_audio_chat_node import GeminiAudioChat
from .gemini_audio_recorder_node import GeminiAudioRecorder
from .multi_images_input import MultiImagesInput

NODE_CLASS_MAPPINGS = {
    "Gemini 3.x Pro": Gemini3xPro,
    "Gemini Image Gen": GeminiImageGen,
    "Gemini Video Gen": GeminiVideoGen,
    "Gemini TTS": GeminiTTS,
    "Gemini Audio Chat": GeminiAudioChat,
    "Gemini Audio Recorder": GeminiAudioRecorder,
    "Multi Images Input": MultiImagesInput,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Gemini 3.x Pro": "🧠 Gemini 3.x Pro Multimodal",
    "Gemini Image Gen": "🎨 Gemini Image Generation",
    "Gemini Video Gen": "🎬 Gemini Video Generation",
    "Gemini TTS": "🔊 Gemini Text-to-Speech",
    "Gemini Audio Chat": "🎙️ Gemini Live Audio Chat",
    "Gemini Audio Recorder": "🎤 Audio Recorder Gemini",
    "Multi Images Input": "📸 Multi Images Input",
}

WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
