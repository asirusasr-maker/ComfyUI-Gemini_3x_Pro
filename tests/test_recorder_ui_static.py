from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "js" / "gemini_ui.js").read_text(encoding="utf-8")
PY = (ROOT / "gemini_audio_recorder_node.py").read_text(encoding="utf-8")

def test_recorder_is_output_node():
    assert "OUTPUT_NODE = True" in PY

def test_button_is_present_and_native():
    assert 'node.addWidget(' in JS
    assert '"button"' in JS
    assert 'BUTTON_NAME = "gemini_start_record"' in JS

def test_button_is_not_serialized():
    assert 'button.serialize = false' in JS
    assert 'button.options.serialize = false' in JS

def test_trigger_is_bumped_before_queue():
    assert 'trigger.value = current + 1' in JS
    assert 'app.queuePrompt' in JS
