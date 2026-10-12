"""SttClient: 음성 → 텍스트 (Groq Whisper)."""
import os


class SttClient:
    def __init__(self, groqClient=None, model: str = "whisper-large-v3-turbo"):
        if groqClient is None:
            from groq import Groq
            groqClient = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.groqClient = groqClient
        self.model = model

    def transcribe(self, speech: bytes) -> str:
        result = self.groqClient.audio.transcriptions.create(
            file=("speech.wav", speech),
            model=self.model,
            language="ko",
            # 여행 용어를 미리 알려주면 오인식이 줄어든다
            prompt="여행 상품, 허니문, 효도, 골프, 트레킹, 클래식, 그랜드, 프리미엄, 샴페인, 파인다이닝",
        )
        return result.text.strip()
