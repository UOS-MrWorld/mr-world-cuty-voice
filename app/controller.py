"""VoiceController: VAD → STT → Parser → Validator 순서로 처리하고 VoiceResponse를 만든다."""
from .models import ScreenContext, VoiceCommand, VoiceResponse
from .parser import CommandParser
from .stt import SttClient
from .vad import VadDetector
from .validator import CommandValidator

# 실수로 실행되면 곤란한 명령은 바로 실행하지 않고 한 번 더 묻는다
NEEDS_CONFIRM = {"checkout": "예약 신청 화면으로 이동할까요?"}


class VoiceController:
    def __init__(self, vad=None, stt=None, parser=None, validator=None):
        self.vad = vad or VadDetector()
        self.stt = stt or SttClient()
        self.parser = parser or CommandParser()
        self.validator = validator or CommandValidator()

    def handleVoiceCommand(self, audio: bytes, context: ScreenContext) -> VoiceResponse:
        speech = self.vad.extractSpeech(audio)
        if not speech:
            return VoiceResponse(recognizedText="", commands=[VoiceCommand(
                action="unknown", params={"message": "말소리가 들리지 않았어요. 다시 말씀해 주세요."})])
        text = self.stt.transcribe(speech)
        return self._fromText(text, context)

    def _fromText(self, text: str, context: ScreenContext) -> VoiceResponse:
        """STT 이후 단계. 텍스트로 바로 테스트할 때도 이 함수를 쓴다."""
        if not text:
            return VoiceResponse(recognizedText="", commands=[VoiceCommand(
                action="unknown", params={"message": "잘 못 알아들었어요. 다시 말씀해 주세요."})])
        commands = self.validator.validate(self.parser.parse(text, context), context)

        out, pending = [], {}
        for c in commands:
            if c.action == "confirm":
                if context.pendingAction:  # "응" → 기다리던 명령 실행
                    out.append(VoiceCommand(action=context.pendingAction))
                continue
            if c.action in NEEDS_CONFIRM:
                pending = {"action": c.action, "message": NEEDS_CONFIRM[c.action]}
                continue
            out.append(c)
        if not out and not pending:
            out = [VoiceCommand(action="unknown", params={"message": "무엇을 확인할지 모르겠어요. 다시 말씀해 주세요."})]
        return VoiceResponse(recognizedText=text, commands=out, pending=pending)
