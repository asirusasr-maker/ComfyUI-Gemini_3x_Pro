"""
Gemini Text-to-Speech Node
Handles audio/l16 (raw PCM), MP3, WAV from Gemini TTS API
Returns proper ComfyUI AUDIO dict format
"""

import os
import json
import io
import re
import torch
import numpy as np

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

try:
    import torchaudio
    HAS_TORCHAUDIO = True
except ImportError:
    HAS_TORCHAUDIO = False


class GeminiTTS:
    CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

    TTS_MODELS = [
        "gemini-3.1-flash-tts-preview",
    ]

    VOICES = ["Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede", "Callirhoe"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": "Hello, this is a test."}),
                "model": (cls.TTS_MODELS, {"default": "gemini-3.1-flash-tts-preview"}),
                "voice": (cls.VOICES, {"default": "Puck"}),
            },
            "optional": {
                "speed": ("FLOAT", {"default": 1.0, "min": 0.5, "max": 2.0, "step": 0.1}),
                "pitch": ("FLOAT", {"default": 0.0, "min": -10.0, "max": 10.0, "step": 0.5}),
                "api_key": ("STRING", {"default": ""}),
                "proxy": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("AUDIO", "STRING")
    RETURN_NAMES = ("audio", "tts_info")
    FUNCTION = "generate_speech"
    CATEGORY = "Gemini 3.x"

    def _get_api_key(self, api_key_input):
        if api_key_input and api_key_input.strip():
            return api_key_input.strip()
        if os.path.exists(self.CONFIG_PATH):
            try:
                with open(self.CONFIG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f).get("GEMINI_API_KEY", "")
            except Exception:
                pass
        return os.environ.get("GEMINI_API_KEY", "")

    def _parse_audio_mime_type(self, mime_type):
        """Parse audio/l16; rate=24000; channels=1"""
        rate = 24000
        channels = 1

        if mime_type:
            mt = mime_type.lower()
            rate_match = re.search(r'rate=(\d+)', mt)
            if rate_match:
                rate = int(rate_match.group(1))
            ch_match = re.search(r'channels=(\d+)', mt)
            if ch_match:
                channels = int(ch_match.group(1))

        return rate, channels

    def _make_audio_dict(self, waveform_tensor, sample_rate):
        """Create ComfyUI AUDIO dict. waveform must be [batch, channels, samples]"""
        if waveform_tensor.dim() == 1:
            waveform_tensor = waveform_tensor.unsqueeze(0).unsqueeze(0)
        elif waveform_tensor.dim() == 2:
            waveform_tensor = waveform_tensor.unsqueeze(0)
        return {"waveform": waveform_tensor, "sample_rate": sample_rate}

    def _load_audio_from_bytes(self, audio_bytes, mime_type="audio/mp3"):
        """Load audio bytes into ComfyUI AUDIO dict format"""
        rate, channels = self._parse_audio_mime_type(mime_type)

        # Handle raw PCM (audio/l16)
        if "l16" in mime_type.lower() or "pcm" in mime_type.lower():
            audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32767.0

            if channels > 1:
                samples = len(audio_np) // channels
                audio_np = audio_np[:samples * channels].reshape(-1, channels).T
            else:
                audio_np = audio_np.reshape(1, -1)

            audio_tensor = torch.from_numpy(audio_np).unsqueeze(0)
            return self._make_audio_dict(audio_tensor, rate)

        # Try torchaudio for MP3/WAV/OGG
        if HAS_TORCHAUDIO:
            try:
                buffer = io.BytesIO(audio_bytes)
                fmt = "mp3"
                if "wav" in mime_type.lower():
                    fmt = "wav"
                elif "ogg" in mime_type.lower():
                    fmt = "ogg"
                elif "flac" in mime_type.lower():
                    fmt = "flac"

                waveform, sr = torchaudio.load(buffer, format=fmt)

                if waveform.shape[0] > 1:
                    waveform = waveform.mean(dim=0, keepdim=True)

                if sr != 44100:
                    resampler = torchaudio.transforms.Resample(sr, 44100)
                    waveform = resampler(waveform)
                    sr = 44100

                waveform = waveform.unsqueeze(0)
                return self._make_audio_dict(waveform, sr)
            except Exception as e:
                print(f"[Gemini TTS] torchaudio failed: {e}")

        # Fallback: try wave (WAV only)
        try:
            import wave
            buffer = io.BytesIO(audio_bytes)
            with wave.open(buffer, 'rb') as wav:
                sr = wav.getframerate()
                ch = wav.getnchannels()
                frames = wav.readframes(wav.getnframes())
                audio_np = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0
                if ch > 1:
                    audio_np = audio_np.reshape(-1, ch).T
                else:
                    audio_np = audio_np.reshape(1, -1)
                audio_tensor = torch.from_numpy(audio_np).unsqueeze(0)
                return self._make_audio_dict(audio_tensor, sr)
        except Exception as e:
            print(f"[Gemini TTS] wave fallback failed: {e}")

        return None

    def generate_speech(self, text, model, voice, speed=1.0, pitch=0.0, api_key="", proxy=""):

        if not HAS_GENAI:
            placeholder = self._make_audio_dict(torch.zeros((1, 1, 24000)), 24000)
            return (placeholder, "Error: google-genai not installed")

        key = self._get_api_key(api_key)
        if not key:
            placeholder = self._make_audio_dict(torch.zeros((1, 1, 24000)), 24000)
            return (placeholder, "Error: No API key")

        client = genai.Client(api_key=key)

        try:
            response = client.models.generate_content(
                model=model,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["Audio"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                        )
                    )
                )
            )

            audio_bytes = None
            mime_type = "audio/mp3"

            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    mime_type = part.inline_data.mime_type or "audio/mp3"
                    audio_bytes = part.inline_data.data
                    break

            if not audio_bytes:
                placeholder = self._make_audio_dict(torch.zeros((1, 1, 24000)), 24000)
                return (placeholder, "No audio data in response")

            audio_data = self._load_audio_from_bytes(audio_bytes, mime_type)

            if audio_data is None:
                placeholder = self._make_audio_dict(torch.zeros((1, 1, 24000)), 24000)
                return (placeholder, f"Failed to decode audio. MIME type: {mime_type}")

            info = {
                "model": model,
                "voice": voice,
                "speed": speed,
                "pitch": pitch,
                "text_length": len(text),
                "mime_type": mime_type,
                "sample_rate": audio_data["sample_rate"],
                "duration_sec": audio_data["waveform"].shape[-1] / audio_data["sample_rate"],
            }

            return (audio_data, json.dumps(info, ensure_ascii=False))

        except Exception as e:
            error_msg = str(e)
            print(f"[Gemini TTS] Error: {error_msg}")
            placeholder = self._make_audio_dict(torch.zeros((1, 1, 24000)), 24000)
            return (placeholder, f"Error: {error_msg}")
