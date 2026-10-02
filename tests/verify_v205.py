from pathlib import Path
import ast
import re

ROOT = Path(__file__).resolve().parents[1]
py = (ROOT / 'gemini_audio_recorder_node.py').read_text(encoding='utf-8')
js = (ROOT / 'js' / 'gemini_ui.js').read_text(encoding='utf-8')

ast.parse(py)
assert 'OUTPUT_NODE = True' in py
assert 'GeminiAudioRecorder' in py
assert 'node.addWidget(' in js
assert 'const RECORDER_CLASS = "Gemini Audio Recorder"' in js
assert 'const BUTTON_NAME = "gemini_start_record"' in js
assert 'button.serialize = false' in js
assert 'button.options.serialize = false' in js
assert 'trigger.value = current + 1' in js
assert 'app.queuePrompt' in js
print('v2.0.5 recorder verification: PASS')
