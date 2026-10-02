# ComfyUI-Gemini_3x_Pro v2.0

Полностью переработанная версия нод Gemini для ComfyUI с актуальными моделями Google на октябрь 2026 года.

## Что сделано в v2.0

- автоматический fallback при временных ошибках `408/429/500/502/503/504`;
- exponential backoff + jitter;
- временный cooldown перегруженной модели;
- сначала всегда используется выбранная модель, затем следующая модель из её цепочки;
- `401/403` и обычные клиентские ошибки не ретраятся вслепую;
- AFC отключён в основной мультимодальной ноде, поэтому предупреждение SDK исчезает;
- обновлены модели Text/Multimodal, Image, TTS, Live и Video;
- Video теперь сохраняет реальный MP4 и декодирует его в IMAGE-кадры, если доступны `ffmpeg/ffprobe`;
- Live Audio Chat больше не placeholder — используется реальный Live API WebSocket-сеанс;
- Audio Recorder теперь реально использует выбранный микрофон и имеет ограничение максимальной длительности;
- сохранены Search Grounding, Structured JSON, chat history, Multi Images.

## Актуальные модели

### Text / Multimodal

```text
gemini-3.8-flash
gemini-3.7-flash
gemini-3.6-flash
gemini-3.5-flash
gemini-3.5-flash-lite
gemini-3.1-flash-lite
gemini-3.1-pro-preview
```

### Image / Nano Banana

В UI модели отображаются по официальным названиям Google: 

```text
Nano Banana Pro  → gemini-3-pro-image
Nano Banana 2    → gemini-3.1-flash-image
Nano Banana 2 Lite → gemini-3.1-flash-lite-image
```

Порядок fallback:

```text
Nano Banana Pro
      ↓
Nano Banana 2
      ↓
Nano Banana 2 Lite
```

Nano Banana 2 — основной универсальный вариант; Nano Banana 2 Lite работает только в 1K, поэтому v2.0.1 автоматически снижает `image_size` до 1K при fallback на Lite.


### TTS

```text
gemini-3.8-flash-tts
gemini-3.8-flash-lite-tts
```

### Live

```text
gemini-3.8-live
gemini-3.8-live-extended-thinking
```

### Video

```text
veo-3.1-generate-preview
veo-3.1-fast-generate-preview
veo-3.1-lite-generate-preview
gemini-omni-1.1-flash
```

## Fallback

Для Flash:

```text
gemini-3.8-flash
      ↓
gemini-3.7-flash
      ↓
gemini-3.6-flash
      ↓
gemini-3.5-flash
      ↓
gemini-3.5-flash-lite
      ↓
gemini-3.1-flash-lite
```

Для Pro:

```text
gemini-3.1-pro-preview
      ↓
gemini-3.8-flash
      ↓
gemini-3.7-flash
      ↓
gemini-3.6-flash
      ...
```

Для TTS:

```text
gemini-3.8-flash-tts
      ↓
gemini-3.8-flash-lite-tts
```

Для Image:

```text
gemini-3-pro-image
      ↓
gemini-3.1-flash-image
      ↓
gemini-3.1-flash-lite-image
```

Для Video:

```text
veo-3.1-generate-preview
      ↓
veo-3.1-fast-generate-preview
      ↓
veo-3.1-lite-generate-preview
      ↓
gemini-omni-1.1-flash
```

Когда выбран Omni, он пробуется первым, затем Veo Fast/Lite.

## AFC

AFC — Automatic Function Calling. Он полезен, когда SDK автоматически вызывает функции/tools, предоставленные приложением. В основной ноде v2 таких Python-функций нет, поэтому AFC отключён. Google Search Grounding при этом остаётся доступным как серверный встроенный инструмент.

## Установка

1. Удали или переименуй старую папку `ComfyUI-Gemini_3x_Pro`.
2. Распакуй новую папку сюда:

```text
ComfyUI/custom_nodes/ComfyUI-Gemini_3x_Pro
```

3. Вставь свой API key в `config.json`.
4. Для portable ComfyUI:

```bat
python_embeded\\python.exe -m pip install -r ComfyUI\\custom_nodes\\ComfyUI-Gemini_3x_Pro\\requirements.txt
```

5. Перезапусти ComfyUI.

## Важно для текущей версии

`torch` и `torchaudio` специально не добавлены в `requirements.txt`, чтобы не перезаписать твою CUDA-сборку PyTorch.

Версия SDK:

```text
google-genai>=2.27.0,<3.0
```

## Диагностика

При перегрузке ты увидишь примерно:

```text
[Gemini 3.x Pro] gemini-3.8-flash returned HTTP 503
[Gemini 3.x Pro] Retry 1/1 in 1.9s
gemini-3.8-flash exhausted retries
[Gemini 3.x Pro] Fallback → gemini-3.7-flash
[Gemini 3.x Pro] HTTP 200 OK → gemini-3.7-flash
```

В `usage_info` также сохраняется:

```json
{
  "requested_model": "gemini-3.8-flash",
  "actual_model": "gemini-3.7-flash",
  "fallback_used": true
}
```

## Документация Google

Список моделей: https://ai.google.dev/gemini-api/docs/models  
Image: https://ai.google.dev/gemini-api/docs/image-generation  
Veo: https://ai.google.dev/gemini-api/docs/veo  
Omni: https://ai.google.dev/gemini-api/docs/omni  
TTS: https://ai.google.dev/gemini-api/docs/speech-generation  
Live API: https://ai.google.dev/gemini-api/docs/live-api/get-started-sdk  
Deprecations: https://ai.google.dev/gemini-api/docs/deprecations  
Python SDK: https://googleapis.github.io/python-genai/

## Лицензия

Apache-2.0. См. `LICENSE`.

### Исправление Audio Recorder (v2.0.5)

`Gemini Audio Recorder` теперь является валидной `OUTPUT_NODE`. Это позволяет кнопке **🔴 Start Record** ставить текущий workflow в очередь даже тогда, когда downstream output node отсутствует. Кнопка изменяет `trigger`, запускает обычную очередь ComfyUI и остаётся нативным canvas-widget, поэтому следует за размером ноды.
