"""
Gemini Audio Recorder Node
Records audio from microphone with silence detection
"""

import torch
import torchaudio
import sounddevice as sd
import numpy as np
import os
import time
import folder_paths


class GeminiAudioRecorder:
    @classmethod
    def INPUT_TYPES(cls):
        devices = sd.query_devices()
        input_devices = [d['name'] for d in devices if d['max_input_channels'] > 0]
        return {
            "required": {
                "device": (input_devices, {"default": input_devices[0] if input_devices else "Default"}),
                "sample_rate": ("INT", {"default": 44100, "min": 8000, "max": 96000, "step": 100}),
                "silence_threshold": ("FLOAT", {"default": 0.01, "min": 0.001, "max": 0.1, "step": 0.001}),
                "silence_duration": ("FLOAT", {"default": 2.0, "min": 0.5, "max": 5.0, "step": 0.1}),
                "trigger": ("INT", {"default": 0})
            }
        }

    def __init__(self):
        self.reset_state()

    def reset_state(self):
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            for filename in os.listdir(self.temp_dir):
                if filename.startswith("recorded_audio_") and filename.endswith(".wav"):
                    try:
                        os.remove(os.path.join(self.temp_dir, filename))
                    except Exception:
                        pass
        self.audio_data = []
        self.temp_dir = folder_paths.get_temp_directory()
        self.recorded_file = None
        self.last_trigger = -1

    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("audio",)
    FUNCTION = "record"
    CATEGORY = "Gemini 3.x"

    def record(self, device, sample_rate, silence_threshold, silence_duration, trigger):
        try:
            if trigger != self.last_trigger:
                self.last_trigger = trigger
                audio_chunks = []
                silence_start = None

                with sd.InputStream(device=None, channels=1, samplerate=sample_rate, blocksize=int(sample_rate * 0.1)) as stream:
                    while True:
                        audio_chunk = stream.read(int(sample_rate * 0.1))[0]
                        audio_chunks.append(audio_chunk)

                        if np.max(np.abs(audio_chunk)) < silence_threshold:
                            if silence_start is None:
                                silence_start = time.time()
                            elif time.time() - silence_start >= silence_duration:
                                break
                        else:
                            silence_start = None

                audio_data = np.concatenate(audio_chunks, axis=0)
                for i in range(len(audio_data) - 1, -1, -1):
                    if abs(audio_data[i]) > silence_threshold:
                        audio_data = audio_data[:i + int(sample_rate * 0.2)]
                        break

                audio_tensor = torch.from_numpy(audio_data).float().t()
                temp_file = os.path.join(self.temp_dir, f"recorded_audio_{int(time.time())}.wav")
                torchaudio.save(temp_file, audio_tensor, sample_rate)
                self.recorded_file = temp_file

                waveform, sr = torchaudio.load(self.recorded_file)
                return ({"waveform": waveform.unsqueeze(0), "sample_rate": sr},)

            elif self.recorded_file and os.path.exists(self.recorded_file):
                waveform, sr = torchaudio.load(self.recorded_file)
                return ({"waveform": waveform.unsqueeze(0), "sample_rate": sr},)

        except Exception as e:
            print(f"[Gemini Audio Recorder] Error recording: {e}")

        return ({"waveform": torch.zeros(1, 1, 1), "sample_rate": sample_rate},)
