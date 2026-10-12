"""마이크 입력 → Silero VAD로 발화 구간 검출 → Groq Whisper로 텍스트 변환.

사용법: python scripts/mic_vad.py  (종료: Ctrl+C)
"""
import collections
import io
import os
import queue
import wave

import numpy as np
import sounddevice as sd
import torch
from dotenv import load_dotenv
from groq import Groq
from silero_vad import VADIterator, load_silero_vad

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SR = 16000            # Silero VAD는 16kHz
CHUNK = 512           # 약 32ms 단위로 판단
SILENCE_MS = 700      # 0.7초 조용하면 발화 종료로 판단

model = load_silero_vad()
vad = VADIterator(model, sampling_rate=SR, min_silence_duration_ms=SILENCE_MS)
audio_q: "queue.Queue[np.ndarray]" = queue.Queue()


def on_audio(indata, frames, time, status):
    audio_q.put(indata[:, 0].copy())


def to_wav(samples: np.ndarray) -> bytes:
    pcm = (np.clip(samples, -1, 1) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def transcribe(samples: np.ndarray) -> str:
    result = client.audio.transcriptions.create(
        file=("speech.wav", to_wav(samples)),
        model="whisper-large-v3-turbo",
        language="ko",
    )
    return result.text


def main():
    preroll = collections.deque(maxlen=10)   # 발화 시작 직전 약 0.3초 보존 (앞부분 잘림 방지)
    recording, buffer = False, []
    print("🎤 말해보세요 (종료: Ctrl+C)")
    with sd.InputStream(samplerate=SR, channels=1, dtype="float32",
                        blocksize=CHUNK, callback=on_audio):
        while True:
            chunk = audio_q.get()
            event = vad(torch.from_numpy(chunk))

            if event and "start" in event:
                recording = True
                buffer = list(preroll)
                print("🟢 발화 시작")

            if recording:
                buffer.append(chunk)
            else:
                preroll.append(chunk)

            if event and "end" in event:
                recording = False
                print("🔴 발화 종료 → 인식 중...")
                print("📝", transcribe(np.concatenate(buffer)))
                vad.reset_states()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n종료")
