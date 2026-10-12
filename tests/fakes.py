"""테스트용 가짜 Groq/VAD — 인터넷·API 키 없이 파이프라인을 검증한다."""
import json
from types import SimpleNamespace

# FE 여행상품 목록 화면(/tours)에 보이는 순서 그대로 보낸다고 가정한 샘플
SAMPLE_TOURS = [
    {"tourId": 11, "tourName": "발리 허니문 5일", "theme": "HONEYMOON", "price": 1890000},
    {"tourId": 23, "tourName": "제주 효도 힐링 3일", "theme": "HEALING", "price": 690000},
    {"tourId": 37, "tourName": "다낭 골프 4일", "theme": "GOLF", "price": 1290000},
    {"tourId": 42, "tourName": "알프스 트레킹 7일", "theme": "TREKKING", "price": 3200000},
]


class FakeLLM:
    """chat.completions.create(...)가 미리 정한 JSON을 돌려준다."""
    def __init__(self, answer):
        self.answer = answer
        self.last_user = None
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.last_user = json.loads(kw["messages"][1]["content"])
        content = self.answer if isinstance(self.answer, str) else json.dumps(self.answer)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


class FakeSTT:
    def __init__(self, text):
        self.text = text

    def transcribe(self, speech):
        return self.text


class FakeVAD:
    def __init__(self, speech=b"speech"):
        self.speech = speech

    def extractSpeech(self, audio):
        return self.speech
