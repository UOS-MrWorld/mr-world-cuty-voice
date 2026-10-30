"""FastAPI 서버. 실행: uvicorn app.main:app --reload --port 8000"""
import json
import os

from dotenv import load_dotenv
import groq
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError

from . import errors
from .controller import VoiceController
from .errors import ApiError
from .models import ScreenContext, VoiceResponse

load_dotenv()
app = FastAPI(title="Mr.CUTY Voice AI Server")
errors.register(app)
MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10MB ≈ 16kHz WAV 5분
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://localhost:8000").split(","),
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

_controller: VoiceController | None = None


def controller() -> VoiceController:
    global _controller
    if _controller is None:
        _controller = VoiceController()
    return _controller


def _context(raw: str) -> ScreenContext:
    try:
        return ScreenContext(**json.loads(raw or "{}"))
    except (json.JSONDecodeError, ValidationError, TypeError):
        raise ApiError(400, "context 형식이 올바르지 않습니다. ScreenContext JSON 문자열을 보내 주세요.")


def _run(fn, *args):
    """외부 음성 모델(Groq) 실패를 공통 에러 형식으로 바꾼다."""
    try:
        return fn(*args)
    except groq.RateLimitError:
        raise ApiError(503, "음성 인식 요청이 많아 잠시 후 다시 시도해 주세요.")
    except groq.APIError:
        raise ApiError(503, "음성 인식 서비스에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/voice/command", response_model=VoiceResponse)
async def voice_command(audio: UploadFile = File(...), context: str = Form("{}")):
    """audio: 16kHz 모노 WAV, context: ScreenContext JSON 문자열."""
    data = await audio.read()
    if not data:
        raise ApiError(400, "오디오 파일이 비어 있습니다.")
    if len(data) > MAX_AUDIO_BYTES:
        raise ApiError(400, "오디오 파일이 너무 큽니다. 10MB 이하로 보내 주세요.")
    ctx = _context(context)
    try:
        return _run(controller().handleVoiceCommand, data, ctx)
    except ValueError as e:  # WAV 형식 오류 (16kHz·모노·16bit가 아님)
        raise ApiError(400, str(e))


class TextRequest(BaseModel):
    text: str
    context: ScreenContext = ScreenContext()


@app.post("/api/v1/voice/text", response_model=VoiceResponse)
def voice_text(req: TextRequest):
    """개발·검증용: 마이크 없이 문장으로 바로 테스트 (VAD·STT 단계 생략)."""
    if not req.text.strip():
        raise ApiError(400, "text가 비어 있습니다.")
    return _run(controller()._fromText, req.text, req.context)


# 데모 페이지: http://localhost:8000/demo/
app.mount("/demo", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "demo"), html=True), name="demo")
