# mr-world-cuty-voice

Mr.CUTY(Curate Your Travel) 서비스의 **음성인식 AI 서버**입니다.
고객이 말로 여행 상품을 검색·선택·구성하고, 신청 화면 직전까지 진행할 수 있도록 음성을 JSON 명령으로 바꿉니다.

```
마이크 → Silero VAD → Groq Whisper → Groq GPT-OSS 120B → 검증 → JSON 명령 → FE → BE
```

설계: [docs/pipeline.md](docs/pipeline.md) · M2 결과: [docs/m2.md](docs/m2.md)

## 폴더

```
app/          서버 (클래스도와 같은 이름)
  main.py        FastAPI 엔드포인트
  controller.py  VoiceController
  vad.py         VadDetector
  stt.py         SttClient
  parser.py      CommandParser
  validator.py   CommandValidator
  models.py      ScreenContext / VoiceCommand / VoiceResponse
demo/         여행상품 선택 연동 데모 페이지
tests/        자동 테스트 (Groq 없이 실행)
scripts/      stt_file.py(파일 STT), mic_vad.py(마이크+VAD), verify_select.py(실제 Groq 연동 검증)
```

## 설치

Python 3.11 권장.

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # GROQ_API_KEY 채우기
```

## 실행

```bash
uvicorn app.main:app --reload --port 8000
```

- 데모: http://localhost:8000/demo/ (🎤 말하기 또는 문장 입력)
- API 문서: http://localhost:8000/docs

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | /api/v1/voice/command | `audio`(16kHz 모노 WAV) + `context`(ScreenContext JSON) → VoiceResponse |
| POST | /api/v1/voice/text | 개발용: `{text, context}` → VoiceResponse (VAD·STT 생략) |
| GET | /health | 상태 확인 |

## 테스트

```bash
pytest                          # 자동 테스트 16개 (API 키 필요 없음)
python scripts/verify_select.py # 실제 Groq로 발화 13개 검증 → docs/verification_result.md
```

## 진행 상황

- [x] 파이프라인 구조 설계
- [x] 마이크 + VAD 발화 검출 (`scripts/mic_vad.py`)
- [x] 텍스트 → JSON 명령 변환 (GPT-OSS) + 검증기
- [x] FastAPI 엔드포인트 (`POST /api/v1/voice/command`)
- [x] 여행상품 선택 연동 검증 (자동 테스트 + 데모 페이지)
- [ ] 실제 FE 화면에 연결
- [ ] 실시간 VAD 스트리밍 (최종 발표)
