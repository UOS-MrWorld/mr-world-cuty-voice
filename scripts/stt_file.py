"""녹음 파일을 Groq Whisper로 텍스트 변환하는 테스트.

사용법: python scripts/stt_file.py sample.m4a
"""
import os
import sys

from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def transcribe_file(path: str) -> str:
    with open(path, "rb") as f:
        result = client.audio.transcriptions.create(
            file=(os.path.basename(path), f.read()),
            model="whisper-large-v3-turbo",
            language="ko",
        )
    return result.text


if __name__ == "__main__":
    audio_path = sys.argv[1] if len(sys.argv) > 1 else "sample.m4a"
    print(transcribe_file(audio_path))
