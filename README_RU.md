# 🧠 ComfyUI-Gemini_3x_Pro

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![ComfyUI](https://img.shields.io/badge/ComfyUI-0.33+-green.svg)](https://github.com/comfyanonymous/ComfyUI)
[![Google GenAI](https://img.shields.io/badge/google--genai-2.x-orange.svg)](https://pypi.org/project/google-genai/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

> **Продвинутые ноды Gemini 3.x для ComfyUI** — мультимодальный ИИ-конвейер с поддержкой текста, изображений, аудио, видео, TTS, живого чата и записи звука. Построен на актуальном SDK `google-genai` (v2.x) с полной поддержкой моделей серии Gemini 3.x.

---

## 📑 Содержание

- [Возможности](#-возможности)
- [Установка](#-установка)
- [Зависимости](#-зависимости)
- [Настройка API-ключа](#-настройка-api-ключа)
- [Обзор нод](#-обзор-нод)
- [Доступные модели и лимиты](#-доступные-модели-и-лимиты)
- [Настройка прокси](#-настройка-прокси)
- [Режим чата](#-режим-чата)
- [Важные замечания](#-важные-замечания)
- [Решение проблем](#-решение-проблем)
- [Лицензия](#-лицензия)

---

## ✨ Возможности

- 🧠 **Мультимодальный анализ** — текст + изображения + аудио + видео в одном запросе
- 🎨 **Нативная генерация изображений** — модели Gemini Nano Banana (требуется Paid-тариф)
- 🎬 **Генерация видео** — Veo 3.1 preview (требуется Paid-тариф)
- 🔊 **Text-to-Speech** — 8 голосов, автоопределение форматов PCM/L16/MP3
- 🎙️ **Живой аудио-чат** — заготовка для real-time стриминга
- 🎤 **Аудио-рекордер** — встроенная запись с микрофона с детекцией тишины
- 📸 **Multi Images Input** — объединение до 16 изображений в один батч
- 💬 **Постоянный режим чата** — история диалога сохраняется между запусками workflow
- 🔍 **Search Grounding** — интеграция с Google Search (на выбранных моделях)
- 📐 **Структурированный JSON-вывод** — ответы с валидацией по схеме

---

## 🚀 Установка

### Способ 1: Git Clone (рекомендуется)

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/asirusasr-maker/ComfyUI-Gemini_3x_Pro.git
cd ComfyUI-Gemini_3x_Pro
```

Для **портативной** версии ComfyUI:
```bash
..\..\python_embeded\python.exe -m pip install -r requirements.txt
```

Для **стандартной** версии ComfyUI:
```bash
pip install -r requirements.txt
```

### Способ 2: ComfyUI Manager

1. Откройте ComfyUI → **Manager** → **Install Custom Nodes**
2. Нажмите **Load From File** → выберите скачанный ZIP
3. Перезапустите ComfyUI

---

## 📦 Зависимости

Все необходимые пакеты перечислены в `requirements.txt`:

```
google-genai>=2.0.0
pillow>=10.0.0
numpy>=1.24.0
sounddevice>=0.4.0
```

| Пакет | Версия | Назначение |
|---------|---------|---------|
| `google-genai` | `>=2.0.0` | **Обязательно.** Официальный SDK Google GenAI v2 |
| `pillow` | `>=10.0.0` | Обработка изображений |
| `numpy` | `>=1.24.0` | Операции с тензорами |
| `sounddevice` | `>=0.4.0` | Ввод с микрофона (Audio Recorder) |

> 💡 `torch` и `torchaudio` **не включены** в `requirements.txt`, потому что ComfyUI уже предоставляет их. Установка их отдельно может перезаписать ваш PyTorch с CUDA на CPU-версию.

---

## 🔑 Настройка API-ключа

1. Перейдите в **[Google AI Studio](https://aistudio.google.com/app/apikey)**
2. Нажмите **"Create API Key"**
3. Скопируйте ключ

### Вариант A: Файл конфигурации
Отредактируйте `config.json` в папке ноды:
```json
{
    "GEMINI_API_KEY": "your_api_key_here"
}
```

### Вариант B: Переменная окружения
```bash
set GEMINI_API_KEY=your_api_key_here
```

### Вариант C: Ввод в ноду
Вставьте ключ напрямую в поле `api_key` любой ноды.

---

## 🧩 Обзор нод

> 📷 **Скриншоты:** разместите скриншоты нод в папке `docs/images/`.

---

### 🧠 Gemini 3.x Pro Multimodal

<img src="docs/images/gemini_3x_pro.png" width="400" alt="Gemini 3.x Pro Multimodal">

Основная мультимодальная нода. Принимает **текст, изображения, видео и аудио** одновременно.

**Входы:**
| Название | Тип | Описание |
|------|------|-------------|
| `prompt` | STRING | Основной текстовый промпт |
| `images` | IMAGE | Одно или несколько изображений |
| `video` | IMAGE | Кадры видео (до 16) |
| `audio` | AUDIO | Аудио-волна (dict) |
| `system_instruction` | STRING | Системный промпт |
| `model` | COMBO | Выбор модели Gemini |
| `operation_mode` | COMBO | `analysis` / `chat` / `structured_json` |
| `temperature` | FLOAT | 0.0 – 2.0 |
| `max_output_tokens` | INT | До 65536 |
| `use_search_grounding` | BOOLEAN | Включить Google Search |
| `chat_mode` | BOOLEAN | Включить постоянный чат |
| `clear_history` | BOOLEAN | Сбросить диалог |
| `json_schema` | STRING | JSON-схема для структурированного вывода |

**Выходы:** `generated_content`, `raw_response`, `usage_info`

---

### 🎨 Gemini Image Generation

<img src="docs/images/gemini_image_gen.png" width="400" alt="Gemini Image Generation">

Генерирует изображения с помощью моделей **Nano Banana** через Interactions API.

**Входы:**
| Название | Тип | Описание |
|------|------|-------------|
| `prompt` | STRING | Описание изображения |
| `model` | COMBO | `gemini-3.1-flash-image`, `gemini-3-pro-image` и др. |
| `aspect_ratio` | COMBO | `1:1`, `16:9`, `9:16`, `4:3`, `3:4`, `21:9` |
| `reference_image` | IMAGE | Референс стиля/персонажа |
| `negative_prompt` | STRING | Чего избегать |
| `num_images` | INT | 1 – 4 |

**Выходы:** `generated_images`, `generation_info`, `raw_response`

> ⚠️ **Требуется Paid-тариф.** На Free tier лимит `0/0` — нода вернёт чёрную заглушку.

---

### 🎬 Gemini Video Generation

<img src="docs/images/gemini_video_gen.png" width="400" alt="Gemini Video Generation">

Генерирует видеоклипы с помощью **Veo 3.1**.

**Входы:**
| Название | Тип | Описание |
|------|------|-------------|
| `prompt` | STRING | Описание видео |
| `model` | COMBO | `veo-3.1-generate-preview`, `veo-3.1-lite-generate-preview` |
| `duration` | COMBO | `3s`, `5s`, `8s`, `10s` |
| `aspect_ratio` | COMBO | `16:9`, `9:16`, `1:1` |
| `reference_image` | IMAGE | Референс первого кадра |

**Выходы:** `video_frames`, `video_info`, `raw_response`

> ⚠️ **Требуется Paid-тариф.** На Free tier доступа к Veo нет.

---

### 🔊 Gemini Text-to-Speech

<img src="docs/images/gemini_tts.png" width="400" alt="Gemini TTS">

Преобразует текст в речь с помощью моделей Gemini TTS. Автоопределение форматов `audio/l16`, `audio/mp3`, `audio/wav`.

**Входы:**
| Название | Тип | Описание |
|------|------|-------------|
| `text` | STRING | Текст для озвучки |
| `model` | COMBO | `gemini-3.1-flash-tts-preview` |
| `voice` | COMBO | `Puck`, `Charon`, `Kore`, `Fenrir`, `Leda`, `Orus`, `Aoede`, `Callirhoe` |
| `speed` | FLOAT | Скорость воспроизведения (0.5 – 2.0) |
| `pitch` | FLOAT | Сдвиг тона (-10 – +10) |

**Выходы:** `audio` (ComfyUI AUDIO dict), `tts_info`

---

### 🎙️ Gemini Live Audio Chat

<img src="docs/images/gemini_audio_chat.png" width="400" alt="Gemini Live Audio Chat">

Заготовка для будущей интеграции **Live API** (WebSocket/async стриминг).

**Входы:** `text_input`, `system_prompt`, `audio_input`

**Выходы:** `audio_output`, `text_response`, `session_info`

> 📝 В данный момент возвращает заглушку. Полная реализация требует asyncio WebSocket.

---

### 🎤 Audio Recorder Gemini

<img src="docs/images/audio_recorder.png" width="400" alt="Audio Recorder">

Записывает звук с микрофона с **детекцией тишины**. Нажмите кнопку **🎤 Start Recording** — запись остановится автоматически после `silence_duration` секунд тишины (или через 10 сек максимум).

**Входы:**
| Название | Тип | Описание |
|------|------|-------------|
| `device` | COMBO | Устройство микрофона |
| `sample_rate` | INT | 8000 – 96000 Гц |
| `silence_threshold` | FLOAT | Порог амплитуды (0.001 – 0.1) |
| `silence_duration` | FLOAT | Остановка после N секунд тишины |

**Выходы:** `audio` (ComfyUI AUDIO dict)

---

### 📸 Multi Images Input

<img src="docs/images/multi_images.png" width="400" alt="Multi Images Input">

Объединяет до **16 отдельных изображений** в один батч-тензор.

**Входы:** `image_1` … `image_16` (опционально)

**Выходы:** `images` (батч-тензор IMAGE)

---

## 🚦 Доступные модели и лимиты

> Все лимиты указаны для **Free tier**. На Paid tier лимиты значительно выше.

### 🧠 Текстовые / Мультимодальные модели

| Модель | RPM | TPM | RPD | Search Grounding | Статус |
|-------|-----|-----|-----|------------------|--------|
| `gemini-3.7-flash` | 15 | 1M | 1500 | ❌ | ✅ GA |
| `gemini-3.6-flash` | 15 | 1M | 1500 | ❌ | ✅ GA |
| `gemini-3.5-flash` | 15 | 1M | 1500 | ❌ | ✅ GA |
| `gemini-3.5-flash-lite` | 15 | 1M | 1500 | ✅ 500/день | ✅ GA |
| `gemini-3.1-flash-lite` | 15 | 1M | 1500 | ❌ | ✅ GA |
| `gemini-3.1-pro` | 15 | 1M | 1500 | ❌ | ✅ GA |
| `gemini-3.1-flash-live-preview` | 15 | 1M | 1500 | ❌ | 🔬 Preview |
| `gemini-flash-latest` | 15 | 1M | 1500 | ❌ | ✅ Alias |
| `gemini-pro-latest` | 15 | 1M | 1500 | ❌ | ✅ Alias |

### 🎨 Генерация изображений (Nano Banana)

| Модель | Free Tier | Paid Tier | Статус |
|-------|-----------|-----------|--------|
| `gemini-3.1-flash-image` | **0/0** ❌ | ✅ ~$0.01–0.04/изображение | ✅ GA |
| `gemini-3-pro-image` | **0/0** ❌ | ✅ ~$0.01–0.04/изображение | ✅ GA |
| `gemini-3.1-flash-lite-image` | **0/0** ❌ | ✅ ~$0.01–0.04/изображение | ✅ GA |

> ⚠️ На Free tier эти модели возвращают **429 RESOURCE_EXHAUSTED**. Нода выведет чёрную заглушку + текст ошибки вместо краша.

### 🎬 Генерация видео (Veo)

| Модель | Free Tier | Paid Tier | Статус |
|-------|-----------|-----------|--------|
| `veo-3.1-generate-preview` | **0/0** ❌ | ✅ Paid | 🔬 Preview |
| `veo-3.1-lite-generate-preview` | **0/0** ❌ | ✅ Paid | 🔬 Preview |
| `gemini-omni-flash` | **0/0** ❌ | ✅ Paid | 🔬 Preview |

### 🔊 Text-to-Speech

| Модель | RPM | TPM | RPD | Статус |
|-------|-----|-----|-----|--------|
| `gemini-3.1-flash-tts-preview` | 3 | 10K | 10 | 🔬 Preview |

---

## 🌐 Настройка прокси

Поле `proxy` позволяет маршрутизировать запросы API через промежуточный сервер.

**Зачем использовать прокси?**
- **Региональные блокировки** — Google AI Studio может быть недоступен в вашей стране
- **Более быстрый маршрут** — подключение через ближайший сервер
- **Приватность** — скрыть ваш прямой IP

**Формат:**
```
http://ip:port
http://user:pass@proxy.com:3128
```

Оставьте пустым, если Google API доступен напрямую в вашем регионе.

---

## 💬 Режим чата

Включите постоянные диалоги, которые **сохраняются между запусками workflow**.

### Как использовать

1. Установите `chat_mode: true`
2. Отправьте первый промпт → Gemini отвечает
3. **Измените только промпт** → оставьте `chat_mode: true`
4. Gemini помнит предыдущий контекст и отвечает соответственно
5. Установите `clear_history: true` → Queue → начнётся **новый диалог**

### Пример workflow

| Шаг | Промпт | chat_mode | clear_history | Результат |
|------|--------|-----------|---------------|--------|
| 1 | "Расскажи про Узбекистан" | true | false | Полное описание |
| 2 | "Как называется столица?" | true | false | "Ташкент" (помнит контекст!) |
| 3 | "Объясни квантовую физику" | true | **true** | Новая тема, память о Узбекистане сброшена |

> 📝 История хранится **по модели** в RAM. При перезапуске ComfyUI история сбрасывается.

---

## ⚠️ Важные замечания

### 1. Генерация изображений и видео = только Paid
По состоянию на август 2026, Google установил **лимит 0/0** для генерации изображений и видео на Free tier. Вы **должны** привязать банковскую карту в [Google AI Studio](https://aistudio.google.com/app/apikey) для использования этих функций.

**Альтернатива для Free-пользователей:**
- Используйте **Stable Diffusion / SDXL / Flux** внутри ComfyUI для изображений
- Используйте **MiniMax H3** или другие локальные видео-модели для видео

### 2. Ограничения Search Grounding
- `gemini-3.1-flash-lite` + Search Grounding = **429 ошибка** на Free tier
- Используйте `gemini-3.5-flash-lite` или `gemini-2.0-flash` (если активна) для бесплатного поиска
- Или полностью отключите `use_search_grounding`

### 3. Устаревшие параметры
Для моделей Gemini 3.x параметры `temperature`, `top_p` и `top_k` помечены Google как **deprecated**, но пока работают. Они могут быть удалены в будущих версиях API.

### 4. Формат аудио
Нода принимает нативный ComfyUI `AUDIO` dict (`{"waveform": tensor, "sample_rate": int}`). Аудио автоматически конвертируется в WAV и отправляется в Gemini как `types.Part.from_bytes()`.

---

## 🔧 Решение проблем

| Проблема | Причина | Решение |
|---------|-------|----------|
| `google-genai not installed` | Отсутствует зависимость | `pip install -r requirements.txt` |
| `No API key` | Ключ не задан | Добавьте в `config.json` или в ноду |
| `429 Too Many Requests` | Превышен лимит | Подождите 1 минуту; проверьте лимиты модели |
| `429 с Image Gen` | Free tier заблокирован | Перейдите на Paid tier |
| `'dict' object has no attribute 'cpu'` | Старая версия ноды | Обновитесь до v14+ |
| `Input should be a valid dictionary` | Аудио как dict, не Part | Обновитесь до v14+ |
| История чата сбрасывается | Разный хеш от промпта | Обновитесь до v9+ (фикс session ID) |
| Чёрное изображение на выходе | Image Gen на Free tier | Нормально — API лимит 0/0 |
| TTS выдаёт тишину | Несовпадение формата аудио | Обновитесь до v7+ (поддержка L16/MP3/WAV) |

---

## 📄 Лицензия

Лицензия Apache License, Version 2.0. Подробности в файле [LICENSE](LICENSE).

```
Copyright 2026 ComfyUI-Gemini_3x_Pro Contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

---

## 🙏 Благодарности

- Построено на [Google GenAI SDK](https://github.com/googleapis/python-genai)
- Вдохновлено [ComfyUI-Gemini_Flash_2.0_Exp](https://github.com/ShmuelRonen/ComfyUI-Gemini_Flash_2.0_Exp) от ShmuelRonen
- Audio Recorder основан на community-нодах с детекцией тишины

---

*Последнее обновление: август 2026*
