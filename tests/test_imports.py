import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gemini_common  # noqa: E402


def test_catalog_has_no_legacy_aliases():
    source = (Path(__file__).resolve().parents[1] / "gemini_common.py").read_text(encoding="utf-8")
    for old in (
        "gemini-flash-latest",
        "gemini-pro-latest",
        "gemini-3.1-flash-live-preview",
        "gemini-3.1-flash-tts-preview",
        "gemini-omni-flash",
    ):
        assert old not in source
    assert gemini_common.PRO_MODEL == "gemini-3.1-pro-preview"
