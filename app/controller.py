import logging
import time

from .models import ScreenContext, VoiceCommand, VoiceResponse
from .parser import CommandParser
from .stt import SttClient
from .vad import VadDetector
from .validator import CommandValidator

log = logging.getLogger("voice")

NEEDS_CONFIRM = {"checkout": "예약 신청 화면으로 이동할까요?"}


class VoiceController:
    def __init__(self, vad=None, stt=None, parser=None, validator=None):
        self.vad = vad or VadDetector()
        self.stt = stt or SttClient()
        self.parser = parser or CommandParser()
        self.validator = validator or CommandValidator()

    def handleVoiceCommand(self, audio: bytes, context: ScreenContext) -> VoiceResponse:
        t0 = time.perf_counter()
        speech = self.vad.extractSpeech(audio)
        t1 = time.perf_counter()
        if not speech:
            return VoiceResponse(recognizedText="", commands=[VoiceCommand(
                action="unknown", params={"message": "말소리가 들리지 않았어요. 다시 말씀해 주세요."})])
        text = self.stt.transcribe(speech)
        t2 = time.perf_counter()
        response = self._fromText(text, context)
        t3 = time.perf_counter()
        log.info("voice/command vad=%dms stt=%dms llm=%dms total=%dms",
                 (t1 - t0) * 1000, (t2 - t1) * 1000, (t3 - t2) * 1000, (t3 - t0) * 1000)
        return response

    def _fromText(self, text: str, context: ScreenContext) -> VoiceResponse:
        if not text:
            return VoiceResponse(recognizedText="", commands=[VoiceCommand(
                action="unknown", params={"message": "잘 못 알아들었어요. 다시 말씀해 주세요."})])
        commands = self.validator.validate(self.parser.parse(text, context), context)

        out, pending = [], {}
        for c in commands:
            if c.action == "confirm":
                if context.pendingAction:
                    out.append(VoiceCommand(action=context.pendingAction))
                continue
            if c.action in NEEDS_CONFIRM:
                pending = {"action": c.action, "message": NEEDS_CONFIRM[c.action]}
                continue
            out.append(c)
        if not out and not pending:
            out = [VoiceCommand(action="unknown", params={"message": "무엇을 확인할지 모르겠어요. 다시 말씀해 주세요."})]
        return VoiceResponse(recognizedText=text, commands=out, pending=pending)
