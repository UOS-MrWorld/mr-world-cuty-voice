import json
from types import SimpleNamespace

SAMPLE_TOURS = [
    {"tourId": 11, "tourName": "발리 허니문 5일", "theme": "HONEYMOON", "price": 1890000},
    {"tourId": 23, "tourName": "제주 효도 힐링 3일", "theme": "HEALING", "price": 690000},
    {"tourId": 37, "tourName": "다낭 골프 4일", "theme": "GOLF", "price": 1290000},
    {"tourId": 42, "tourName": "알프스 트레킹 7일", "theme": "TREKKING", "price": 3200000},
]


class FakeLLM:
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
