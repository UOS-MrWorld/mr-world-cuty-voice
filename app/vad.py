"""VadDetector: 오디오에서 사람이 말한 구간만 잘라낸다 (Silero VAD)."""
import io
import wave

import numpy as np

SR = 16000  # Silero VAD는 16kHz 모노만 받는다


def wav_to_samples(data: bytes) -> np.ndarray:
    """16kHz 모노 16bit WAV → float32 배열 (-1~1)."""
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
        self.padMs = padMs        # 말 앞뒤가 잘리지 않게 여유를 둔다
        self.model = None         # 첫 호출 때 로드 (torch가 무거워서 서버 시작을 늦추지 않게)

    def _load(self):
        if self.model is None:
            from silero_vad import load_silero_vad
            self.model = load_silero_vad()
        return self.model

    def extractSpeech(self, audio: bytes) -> bytes:
        """WAV bytes → 발화 구간만 이어붙인 WAV bytes. 말이 없으면 b""."""
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
