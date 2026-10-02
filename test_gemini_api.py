"""Small local connectivity test for ComfyUI-Gemini_3x_Pro v2.0.

Run with ComfyUI portable's embedded Python from the ComfyUI root:
    python_embeded\\python.exe ComfyUI\\custom_nodes\\ComfyUI-Gemini_3x_Pro\\test_gemini_api.py
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from gemini_common import FLASH_MODELS, build_client, get_api_key  # noqa: E402


def main() -> int:
    key = get_api_key("")
    if not key:
        print("[Gemini test] ERROR: GEMINI_API_KEY is not configured.")
        return 2
    try:
        client = build_client(key, "")
        model = FLASH_MODELS[0]
        print(f"[Gemini test] Testing {model} ...")
        response = client.models.generate_content(
            model=model,
            contents="Reply with exactly: GEMINI_OK",
        )
        print("[Gemini test] HTTP request succeeded.")
        print("[Gemini test] Response:", getattr(response, "text", "<no text>"))
        return 0
    except Exception as exc:
        print("[Gemini test] FAILED:", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
