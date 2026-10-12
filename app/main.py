"""FastAPI 서버. 실행: uvicorn app.main:app --reload --port 8000"""
import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError

from .controller import VoiceController
from .models import ScreenContext, VoiceResponse

load_dotenv()
app = FastAPI(title="Mr.CUTY Voice AI Server")
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
    except (json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(400, f"context 형식 오류: {e}")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/voice/command", response_model=VoiceResponse)
async def voice_command(audio: UploadFile = File(...), context: str = Form("{}")):
    """audio: 16kHz 모노 WAV, context: ScreenContext JSON 문자열."""
    data = await audio.read()
    try:
        return controller().handleVoiceCommand(data, _context(context))
    except ValueError as e:
        raise HTTPException(400, str(e))


class TextRequest(BaseModel):
    text: str
    context: ScreenContext = ScreenContext()


@app.post("/api/v1/voice/text", response_model=VoiceResponse)
def voice_text(req: TextRequest):
    """개발·검증용: 마이크 없이 문장으로 바로 테스트 (VAD·STT 단계 생략)."""
    return controller()._fromText(req.text, req.context)


# 데모 페이지: http://localhost:8000/demo/
app.mount("/demo", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "demo"), html=True), name="demo")
