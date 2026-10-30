import io
import os
import wave

import numpy as np

SR = 16000
WINDOW = 512
CONTEXT = 64
MODEL_PATH = os.path.join(os.path.dirname(__file__), "assets", "silero_vad.onnx")


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
    def __init__(self, silenceMs: int = 700, padMs: int = 200, threshold: float = 0.5, minSpeechMs: int = 250):
        self.silenceMs = silenceMs
        self.padMs = padMs
        self.threshold = threshold
        self.minSpeechMs = minSpeechMs
        self.model = None

    def load(self):
        if self.model is None:
            import onnxruntime
            opts = onnxruntime.SessionOptions()
            opts.inter_op_num_threads = 1
            opts.intra_op_num_threads = 1
            self.model = onnxruntime.InferenceSession(MODEL_PATH, sess_options=opts,
                                                      providers=["CPUExecutionProvider"])
        return self.model

    def speechProbs(self, samples: np.ndarray) -> list[float]:
        session = self.load()
        state = np.zeros((2, 1, 128), dtype=np.float32)
        context = np.zeros((1, CONTEXT), dtype=np.float32)
        sr = np.array(SR, dtype=np.int64)
        probs = []
        for start in range(0, len(samples), WINDOW):
            chunk = samples[start:start + WINDOW]
            if len(chunk) < WINDOW:
                chunk = np.pad(chunk, (0, WINDOW - len(chunk)))
            x = np.concatenate([context, chunk[None, :]], axis=1).astype(np.float32)
            out, state = session.run(None, {"input": x, "state": state, "sr": sr})
            context = x[:, -CONTEXT:]
            probs.append(float(out[0][0]))
        return probs

    def timestamps(self, samples: np.ndarray) -> list[dict]:
        probs = self.speechProbs(samples)
        total = len(samples)
        neg = max(self.threshold - 0.15, 0.01)
        minSilence = SR * self.silenceMs / 1000
        minSpeech = SR * self.minSpeechMs / 1000
        pad = int(SR * self.padMs / 1000)

        speeches, current, triggered, tempEnd = [], {}, False, 0
        for i, p in enumerate(probs):
            cur = WINDOW * i
            if p >= self.threshold and tempEnd:
                tempEnd = 0
            if p >= self.threshold and not triggered:
                triggered = True
                current = {"start": cur}
                continue
            if p < neg and triggered:
                if not tempEnd:
                    tempEnd = cur
                if cur - tempEnd < minSilence:
                    continue
                current["end"] = tempEnd
                if current["end"] - current["start"] > minSpeech:
                    speeches.append(current)
                current, triggered, tempEnd = {}, False, 0
        if current and total - current["start"] > minSpeech:
            current["end"] = total
            speeches.append(current)

        for i, s in enumerate(speeches):
            if i == 0:
                s["start"] = max(0, s["start"] - pad)
            if i < len(speeches) - 1:
                gap = speeches[i + 1]["start"] - s["end"]
                if gap < 2 * pad:
                    s["end"] += gap // 2
                    speeches[i + 1]["start"] = max(0, speeches[i + 1]["start"] - gap // 2)
                else:
                    s["end"] = min(total, s["end"] + pad)
                    speeches[i + 1]["start"] = max(0, speeches[i + 1]["start"] - pad)
            else:
                s["end"] = min(total, s["end"] + pad)
        return speeches

    def extractSpeech(self, audio: bytes) -> bytes:
        samples = wav_to_samples(audio)
        stamps = self.timestamps(samples)
        if not stamps:
            return b""
        return samples_to_wav(np.concatenate([samples[s["start"]:s["end"]] for s in stamps]))
