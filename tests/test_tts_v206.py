from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
src = (ROOT / "gemini_tts_node.py").read_text(encoding="utf-8")
ast.parse(src)

required = [
    "gemini-3.8-flash-tts",
    "speech_metadata",
    "custom_voice_id",
    "speaker_profile",
    "inline_vocal_tags",
    "Callirrhoe",
    "Zephyr",
]
for token in required:
    assert token in src, token

print("v2.0.6 TTS Pro static verification: PASS")
