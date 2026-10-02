import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gemini_common import (  # noqa: E402
    FLASH_MODELS,
    PRO_MODEL,
    fallback_chain,
    get_status_code,
    is_model_unavailable,
    is_transient,
    run_with_fallback,
)


class FakeError(Exception):
    def __init__(self, code, message=""):
        super().__init__(f"HTTP {code} {message}")
        self.status_code = code


def test_chain_order():
    assert fallback_chain("gemini-3.6-flash", FLASH_MODELS) == [
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
    ]
    assert fallback_chain(PRO_MODEL, [PRO_MODEL] + FLASH_MODELS) == [PRO_MODEL] + FLASH_MODELS


def test_retry_and_fallback():
    attempts = []

    def request(model):
        attempts.append(model)
        if model == "gemini-3.8-flash":
            raise FakeError(503, "high demand")
        return "ok"

    result, model, used = run_with_fallback(
        ["gemini-3.8-flash", "gemini-3.7-flash"],
        request,
        retries_per_model=0,
        initial_delay=0,
        max_delay=0,
        cooldown_seconds=0,
    )
    assert result == "ok"
    assert model == "gemini-3.7-flash"
    assert used is True
    assert attempts == ["gemini-3.8-flash", "gemini-3.7-flash"]


def test_permanent_auth_error_is_not_transient():
    err = FakeError(401, "UNAUTHENTICATED")
    assert get_status_code(err) == 401
    assert is_transient(err) is False


def test_model_unavailable():
    err = FakeError(404, "model not found")
    assert is_model_unavailable(err) is True
