"""음성 파이프라인 + 여행상품 선택 연동 검증 (가짜 Groq 사용)."""
from datetime import date

from fastapi.testclient import TestClient

from app import main
from app.controller import VoiceController
from app.models import ScreenContext, VoiceCommand
from app.parser import CommandParser
from app.validator import CommandValidator
from tests.fakes import SAMPLE_TOURS, FakeLLM, FakeSTT, FakeVAD

LIST = ScreenContext(screen="list", tours=SAMPLE_TOURS)
CONFIG = ScreenContext(screen="configure", availableTourLevels=["GRAND", "PREMIUM"],
                       drinkOptions=[{"optionId": 1, "name": "샴페인"}, {"optionId": 2, "name": "커피"}])


def make(llm_answer, text="테스트", speech=b"speech"):
    return VoiceController(vad=FakeVAD(speech), stt=FakeSTT(text),
                           parser=CommandParser(groqClient=FakeLLM(llm_answer)),
                           validator=CommandValidator())


def cmds(res):
    return [(c.action, c.params) for c in res.commands]


# ---------- 1. 여행상품 선택 연동 ----------

def test_select_by_order_returns_tourId_on_screen():
    res = make({"commands": [{"action": "select", "params": {"tourId": 23}}]},
               "두 번째 거 보여줘").handleVoiceCommand(b"wav", LIST)
    assert res.recognizedText == "두 번째 거 보여줘"
    assert cmds(res) == [("select", {"tourId": 23})]


def test_select_unknown_tourId_is_blocked():
    # LLM이 화면에 없는 상품(99번)을 지어내면 unknown으로 바꾼다
    res = make({"commands": [{"action": "select", "params": {"tourId": 99}}]}).handleVoiceCommand(b"wav", LIST)
    assert res.commands[0].action == "unknown"


def test_select_with_empty_list_is_blocked():
    res = make({"commands": [{"action": "select", "params": {"tourId": 11}}]}).handleVoiceCommand(
        b"wav", ScreenContext(screen="list", tours=[]))
    assert res.commands[0].action == "unknown"


def test_parser_receives_tours_in_screen_order():
    llm = FakeLLM({"commands": []})
    CommandParser(groqClient=llm).parse("두 번째 거", LIST)
    assert [t["tourId"] for t in llm.last_user["context"]["tours"]] == [11, 23, 37, 42]


def test_search_then_select_in_one_sentence():
    res = make({"commands": [
        {"action": "search", "params": {"theme": "GOLF", "maxPrice": 1500000}},
        {"action": "select", "params": {"tourId": 37}}]}).handleVoiceCommand(b"wav", LIST)
    assert cmds(res) == [("search", {"theme": "GOLF", "maxPrice": 1500000}), ("select", {"tourId": 37})]


# ---------- 2. 검색 ----------

def test_search_month_converted_to_date_range():
    res = make({"commands": [{"action": "search", "params": {"theme": "HEALING", "month": 12}}]}).handleVoiceCommand(b"wav", LIST)
    p = res.commands[0].params
    assert p["theme"] == "HEALING"
    assert p["startDateFrom"].endswith("-12-01") and p["startDateTo"].endswith("-12-31")


def test_convert_month_past_month_goes_next_year():
    parser = CommandParser(groqClient=FakeLLM({}))
    assert parser.convertMonth("3", today=date(2026, 10, 12)) == ("2027-03-01", "2027-03-31")
    assert parser.convertMonth("2", today=date(2027, 1, 5)) == ("2027-02-01", "2027-02-28")


def test_search_drops_wrong_enum():
    res = make({"commands": [{"action": "search", "params": {"theme": "SKI", "keyword": "발리"}}]}).handleVoiceCommand(b"wav", LIST)
    assert cmds(res) == [("search", {"keyword": "발리"})]


# ---------- 3. 구성 / 확인 ----------

def test_configure_filters_invalid_values():
    res = make({"commands": [{"action": "configure", "params": {
        "tourLevel": "CLASSIC", "hotelGrade": "FIVE_STAR", "guestCount": 2,
        "drinkOptions": [{"optionId": 1, "quantity": 1}, {"optionId": 9, "quantity": 1}]}}]}).handleVoiceCommand(b"wav", CONFIG)
    # CLASSIC은 이 화면에서 고를 수 없는 등급, optionId 9는 없는 옵션 → 빠진다
    assert cmds(res) == [("configure", {"hotelGrade": "FIVE_STAR", "guestCount": 2,
                                        "drinkOptions": [{"optionId": 1, "quantity": 1}]})]


def test_checkout_needs_confirmation():
    res = make({"commands": [{"action": "checkout", "params": {}}]}, "이걸로 예약할게").handleVoiceCommand(b"wav", CONFIG)
    assert res.commands == []
    assert res.pending["action"] == "checkout"


def test_confirm_runs_pending_action():
    ctx = CONFIG.model_copy(update={"pendingAction": "checkout"})
    res = make({"commands": [{"action": "confirm", "params": {}}]}, "응").handleVoiceCommand(b"wav", ctx)
    assert cmds(res) == [("checkout", {})]


# ---------- 4. 실패 처리 ----------

def test_no_speech_returns_unknown_without_calling_stt():
    res = make({"commands": []}, speech=b"").handleVoiceCommand(b"wav", LIST)
    assert res.recognizedText == "" and res.commands[0].action == "unknown"


def test_broken_llm_json_returns_unknown():
    res = make("이건 JSON이 아님").handleVoiceCommand(b"wav", LIST)
    assert res.commands[0].action == "unknown"


def test_unknown_action_from_llm_is_dropped():
    res = make({"commands": [{"action": "pay", "params": {}}]}).handleVoiceCommand(b"wav", CONFIG)
    assert res.commands[0].action == "unknown"


# ---------- 5. API ----------

def test_api_voice_command_and_text(monkeypatch):
    fake = make({"commands": [{"action": "select", "params": {"tourId": 11}}]}, "첫 번째 거")
    monkeypatch.setattr(main, "_controller", fake)
    client = TestClient(main.app)
    import json
    r = client.post("/api/v1/voice/command", files={"audio": ("a.wav", b"x", "audio/wav")},
                    data={"context": json.dumps(LIST.model_dump(), ensure_ascii=False)})
    assert r.status_code == 200 and r.json()["commands"] == [{"action": "select", "params": {"tourId": 11}}]
    r = client.post("/api/v1/voice/text", json={"text": "첫 번째 거", "context": LIST.model_dump()})
    assert r.status_code == 200 and r.json()["recognizedText"] == "첫 번째 거"
    assert client.post("/api/v1/voice/command", files={"audio": ("a.wav", b"x")}, data={"context": "{"}).status_code == 400


# ---------- 6. 오디오 형식 ----------

def test_wav_roundtrip_and_format_check():
    import io
    import wave

    import numpy as np
    import pytest

    from app.vad import samples_to_wav, wav_to_samples
    s = np.sin(np.linspace(0, 100, 16000)).astype(np.float32) * 0.5
    assert np.allclose(wav_to_samples(samples_to_wav(s)), s, atol=1e-3)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(b"\0\0" * 10)
    with pytest.raises(ValueError):
        wav_to_samples(buf.getvalue())


# ---------- 7. 구성 전체 흐름 (등급·날짜·다음 단계) ----------

def test_next_action_passes():
    res = make({"commands": [{"action": "next", "params": {}}]}, "다음 단계로 가줘").handleVoiceCommand(b"wav", CONFIG)
    assert cmds(res) == [("next", {})]


def test_departure_date_future_kept_past_dropped():
    from datetime import date, timedelta
    future = (date.today() + timedelta(days=30)).isoformat()
    res = make({"commands": [{"action": "configure", "params": {"departureDate": future, "guestCount": 2}}]}).handleVoiceCommand(b"wav", CONFIG)
    assert cmds(res) == [("configure", {"departureDate": future, "guestCount": 2})]
    res = make({"commands": [{"action": "configure", "params": {"departureDate": "2020-01-01", "guestCount": 2}}]}).handleVoiceCommand(b"wav", CONFIG)
    assert cmds(res) == [("configure", {"guestCount": 2})]
    res = make({"commands": [{"action": "configure", "params": {"departureDate": "2027-02-30"}}]}).handleVoiceCommand(b"wav", CONFIG)
    assert res.commands[0].action == "unknown"


def test_drink_option_remove_with_zero_quantity():
    res = make({"commands": [{"action": "configure", "params": {"drinkOptions": [{"optionId": 2, "quantity": 0}]}}]}).handleVoiceCommand(b"wav", CONFIG)
    assert cmds(res) == [("configure", {"drinkOptions": [{"optionId": 2, "quantity": 0}]})]


def test_parser_sends_today():
    llm = FakeLLM({"commands": []})
    CommandParser(groqClient=llm).parse("11월 20일 출발", CONFIG)
    assert llm.last_user["today"] == date.today().isoformat()


def test_blocked_level_explains_reason():
    res = make({"commands": [{"action": "configure", "params": {"tourLevel": "CLASSIC"}}]}).handleVoiceCommand(b"wav", CONFIG)
    assert res.commands[0].action == "unknown"
    assert "클래식" in res.commands[0].params["message"] and "그랜드" in res.commands[0].params["message"]


# ---------- 8. 공통 에러 응답 형식 (API 명세서) ----------

def _err(r, status, code):
    body = r.json()
    assert r.status_code == status, body
    assert body["status"] == status and body["code"] == code
    assert body["message"] and body["path"].startswith("/") and "T" in body["timestamp"]
    return body


def test_error_format_bad_input(monkeypatch):
    monkeypatch.setattr(main, "_controller", make({"commands": []}))
    client = TestClient(main.app)
    _err(client.post("/api/v1/voice/command", files={"audio": ("a.wav", b"x")}, data={"context": "{"}), 400, "INVALID_INPUT")
    _err(client.post("/api/v1/voice/command", data={"context": "{}"}), 400, "INVALID_INPUT")          # audio 누락
    _err(client.post("/api/v1/voice/command", files={"audio": ("a.wav", b"")}), 400, "INVALID_INPUT")  # 빈 파일
    _err(client.post("/api/v1/voice/text", json={"text": "  "}), 400, "INVALID_INPUT")
    _err(client.get("/api/v1/nope"), 404, "RESOURCE_NOT_FOUND")


def test_error_format_wav_and_groq_failures(monkeypatch):
    import groq
    import httpx

    class BadWavVAD:
        def extractSpeech(self, audio):
            raise ValueError("16kHz / mono / 16bit WAV만 지원합니다")

    class DownSTT:
        def transcribe(self, speech):
            raise groq.APIConnectionError(request=httpx.Request("POST", "https://api.groq.com"))

    client = TestClient(main.app)
    monkeypatch.setattr(main, "_controller", VoiceController(vad=BadWavVAD(), stt=FakeSTT("x"),
                                                             parser=CommandParser(groqClient=FakeLLM({})), validator=CommandValidator()))
    body = _err(client.post("/api/v1/voice/command", files={"audio": ("a.wav", b"x")}), 400, "INVALID_INPUT")
    assert "16kHz" in body["message"]
    monkeypatch.setattr(main, "_controller", VoiceController(vad=FakeVAD(), stt=DownSTT(),
                                                             parser=CommandParser(groqClient=FakeLLM({})), validator=CommandValidator()))
    _err(client.post("/api/v1/voice/command", files={"audio": ("a.wav", b"x")}), 503, "VOICE_SERVICE_UNAVAILABLE")


def test_error_format_unexpected(monkeypatch):
    class Boom:
        def extractSpeech(self, audio):
            raise RuntimeError("boom")
    monkeypatch.setattr(main, "_controller", VoiceController(vad=Boom(), stt=FakeSTT("x"),
                                                             parser=CommandParser(groqClient=FakeLLM({})), validator=CommandValidator()))
    client = TestClient(main.app, raise_server_exceptions=False)
    r = client.post("/api/v1/voice/command", files={"audio": ("a.wav", b"x")}, headers={"Origin": "http://localhost:5173"})
    _err(r, 500, "INTERNAL_SERVER_ERROR")
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"  # 브라우저가 에러 내용을 읽을 수 있어야 함
