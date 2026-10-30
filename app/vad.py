import io
import wave

import numpy as np

SR = 16000


def wav_to_samples(data: bytes) -> np.ndarray:
    with wave.open(io.BytesIO(data), "rb") as w:
        if w.getframerate() != SR or w.getnchannels() != 1 or w.getsampwidth() != 2:
            raise ValueError("16kHz / mono / 16bit WAV만 지원합니다")
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return pcm.astype(np.float32) / 32768.0


def samples_to_wav(samples: np.ndarray) -> bytes:
    pcm = (np.clip(samples, -1, 1) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


class VadDetector:
    def __init__(self, silenceMs: int = 700, padMs: int = 200):
        self.silenceMs = silenceMs
        self.padMs = padMs
        self.model = None

    def _load(self):
        if self.model is None:
            from silero_vad import load_silero_vad
            self.model = load_silero_vad()
        return self.model

    def extractSpeech(self, audio: bytes) -> bytes:
        import torch
        from silero_vad import get_speech_timestamps

        samples = wav_to_samples(audio)
        stamps = get_speech_timestamps(
            torch.from_numpy(samples), self._load(), sampling_rate=SR,
            min_silence_duration_ms=self.silenceMs, speech_pad_ms=self.padMs,
        )
        if not stamps:
            return b""
        speech = np.concatenate([samples[s["start"]:s["end"]] for s in stamps])
        return samples_to_wav(speech)
