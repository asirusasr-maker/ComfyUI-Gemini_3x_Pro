"""ComfyUI microphone recorder with automatic silence detection."""
from __future__ import annotations

import os
import time
from pathlib import Path

import numpy as np
import torch

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except Exception:
    sd = None
    HAS_SOUNDDEVICE = False

try:
    import torchaudio
    HAS_TORCHAUDIO = True
except Exception:
    torchaudio = None
    HAS_TORCHAUDIO = False


class GeminiAudioRecorder:
    CATEGORY = "Gemini 3.x"
    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("audio",)
    FUNCTION = "record"
    # Allows the Start Record UI control to queue this node as a valid
    # workflow output even when the recorder is the only output node.
    OUTPUT_NODE = True

    @staticmethod
    def _devices():
        if not HAS_SOUNDDEVICE:
            return ["Default"]
        try:
            devices = sd.query_devices()
            names = [
                f"{i}: {d['name']}"
                for i, d in enumerate(devices)
                if d.get("max_input_channels", 0) > 0
            ]
            return names or ["Default"]
        except Exception:
            return ["Default"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "device": (cls._devices(), {"default": cls._devices()[0]}),
                "sample_rate": ("INT", {"default": 44100, "min": 8000, "max": 96000, "step": 100}),
                "silence_threshold": ("FLOAT", {"default": 0.01, "min": 0.001, "max": 0.1, "step": 0.001}),
                "silence_duration": ("FLOAT", {"default": 2.0, "min": 0.5, "max": 5.0, "step": 0.1}),
                "max_duration": ("FLOAT", {"default": 10.0, "min": 1.0, "max": 120.0, "step": 0.5}),
                "trigger": ("INT", {"default": 0}),
            }
        }

    def __init__(self):
        self.last_trigger = None
        self.cached_audio = None

    @staticmethod
    def _parse_device(device: str):
        if not HAS_SOUNDDEVICE or device == "Default":
            return None
        try:
            return int(device.split(":", 1)[0])
        except Exception:
            return device

    def _record_once(self, device, sample_rate, silence_threshold, silence_duration, max_duration):
        if not HAS_SOUNDDEVICE:
            raise RuntimeError("sounddevice is not installed")

        device_id = self._parse_device(device)
        block = max(1, int(sample_rate * 0.1))
        chunks = []
        silence_start = None
        started = time.monotonic()

        print(f"[Gemini Audio Recorder] Recording from {device} at {sample_rate} Hz…")
        with sd.InputStream(
            device=device_id,
            channels=1,
            samplerate=sample_rate,
            blocksize=block,
            dtype="float32",
        ) as stream:
            heard_voice = False
            while time.monotonic() - started < float(max_duration):
                chunk, overflowed = stream.read(block)
                if overflowed:
                    print("[Gemini Audio Recorder] Input overflow detected; continuing.")
                chunk = np.asarray(chunk, dtype=np.float32).reshape(-1)
                chunks.append(chunk.copy())
                peak = float(np.max(np.abs(chunk))) if chunk.size else 0.0
                if peak >= silence_threshold:
                    heard_voice = True
                    silence_start = None
                elif heard_voice:
                    if silence_start is None:
                        silence_start = time.monotonic()
                    elif time.monotonic() - silence_start >= float(silence_duration):
                        break

        if not chunks:
            return np.zeros((1, 1), dtype=np.float32)
        audio = np.concatenate(chunks, axis=0)
        # Trim trailing silence, preserving up to 200 ms after last signal.
        if heard_voice:
            non_silent = np.flatnonzero(np.abs(audio) >= silence_threshold)
            if non_silent.size:
                end = min(len(audio), int(non_silent[-1]) + int(sample_rate * 0.2))
                audio = audio[:end]
        return audio.reshape(1, -1)

    def record(self, device, sample_rate, silence_threshold, silence_duration, max_duration, trigger):
        if self.last_trigger == trigger and self.cached_audio is not None:
            return (self.cached_audio,)

        try:
            data = self._record_once(device, sample_rate, silence_threshold, silence_duration, max_duration)
            waveform = torch.from_numpy(data).float().unsqueeze(0)  # [B,C,T]
            self.cached_audio = {"waveform": waveform, "sample_rate": int(sample_rate)}
            self.last_trigger = trigger
            print(f"[Gemini Audio Recorder] Captured {data.shape[-1] / sample_rate:.2f}s")
            return (self.cached_audio,)
        except Exception as exc:
            print(f"[Gemini Audio Recorder] Error: {exc}")
            self.last_trigger = trigger
            self.cached_audio = {"waveform": torch.zeros((1, 1, 1)), "sample_rate": int(sample_rate)}
            return (self.cached_audio,)
