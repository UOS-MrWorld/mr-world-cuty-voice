# CUTY Voice AI

**말로 여행 상품을 찾고, 나만의 여행을 구성하는 음성 기반 AI 기능**

CUTY Voice는 기존 GUI 여행 서비스에 음성 인터페이스를 추가하여 고객이 여행 상품을 더 쉽고 자연스럽게 검색하고 선택할 수 있도록 돕는다.
프로젝트 요구사항에 따라 고객 인터페이스는 GUI를 먼저 구현한 뒤 음성인식 기능을 추가하는 방향으로 확장한다.

## 서비스 소개

고객은 마이크를 통해 원하는 여행 조건을 말할 수 있다.

```text
"부모님과 갈 만한 편안한 여행 찾아줘"
"골프 여행 중에서 프리미엄 등급으로 보여줘"
"이 상품의 호텔을 5성급으로 바꿔줘"
```

음성 AI는 고객의 발화를 분석하여 여행 테마, 투어 등급, 인원, 출발일, 호텔, 교통, 식사 등의 조건을 추출한다. 추출한 조건은 기존 여행 상품 검색 및 옵션 구성 기능과 연결된다.

## 주요 기능

- 음성 입력 및 한국어 음성인식(STT)
- 여행 검색 의도 파악
- 여행 테마 및 검색 조건 추출
- 여행 상품 검색
- 투어 등급·호텔·교통·식사 옵션 변경
- 고객의 발화가 모호할 때 추가 질문
- 음성으로 해석한 결과와 검색 결과를 화면에 표시
- 마이크 권한 거부나 인식 실패 시 GUI·텍스트 입력으로 전환

## 음성 AI 처리 흐름

```text
음성 입력
  → 음성 텍스트 변환
  → 여행 의도와 조건 분석
  → 여행 상품 API 조회 또는 옵션 변경
  → 결과를 화면에 표시
  → 필요한 경우 고객에게 확인
```

> 음성 AI가 해석한 내용을 바로 확정하지 않고 상품 선택·옵션 변경·신청과 같이 중요한 동작은 고객이 결과를 확인한 뒤 진행하도록 하는 방향

## 기존 서비스와의 연결

음성 기능은 기존 client와 server의 여행 도메인을 재사용한다.

| 음성 기능 | 연결할 기존 도메인 |
| --- | --- |
| 여행 상품 검색·상세 조회 | `tour` |
| 회원의 이전 여행 조회 | `member` |
| 여행 신청 시작 | `booking` |
| 음성 입력 및 AI 해석 | `voice` |

음성 AI는 자연어를 기존 API가 사용할 수 있는 검색 조건과 옵션 값으로 변환하는 역할을 담당한다. 실제 상품 존재 여부, 가격, 권한, 신청 가능 여부는 기존 서버가 다시 검증한다.

---

## 구현 (M2 PoC)

```
마이크 → Silero VAD → Groq Whisper → Groq GPT-OSS 120B → 검증 → JSON 명령 → FE → BE
```

설계: [docs/pipeline.md](docs/pipeline.md) · API 명세: [docs/api.md](docs/api.md) · M2 결과: [docs/m2.md](docs/m2.md)

### 폴더

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

### 설치

Python 3.11 권장.

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt   # 서버만 돌릴 땐 requirements.txt
cp .env.example .env                  # GROQ_API_KEY 채우기
```

- 서버 VAD는 Silero VAD ONNX 모델(`app/assets/silero_vad.onnx`, MIT)을 onnxruntime으로 실행한다. torch가 필요 없다.
- `scripts/mic_vad.py`(마이크 실시간 테스트)만 torch 기반 `silero-vad` 패키지를 쓰므로 `requirements-dev.txt`에 포함했다.

### 배포 (Render)

1. Render → New → Blueprint → 이 레포 선택 (`render.yaml` 사용)
2. 환경변수 입력: `GROQ_API_KEY`, `CORS_ORIGINS`(FE 배포 주소, 쉼표로 여러 개)
3. 배포 후 `https://<서비스명>.onrender.com/health` 확인
4. FE 배포 환경변수 `VITE_VOICE_API_BASE_URL=https://<서비스명>.onrender.com/api/v1`

무료 플랜은 15분간 요청이 없으면 잠든다. 발표 전에는 `/health`로 미리 깨워 둔다.

### 실행

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

### 테스트

```bash
pytest                          # 자동 테스트 25개 (API 키 필요 없음)
python scripts/verify_select.py # 실제 Groq로 발화 16개 검증 → docs/verification_result.md
```

### 진행 상황

- [x] 파이프라인 구조 설계
- [x] 텍스트 → JSON 명령 변환 (GPT-OSS) + 검증기 — 실제 Groq로 발화 13개 중 12개 통과 ([결과](docs/verification_result.md))
- [x] FastAPI 엔드포인트 (`POST /api/v1/voice/command`)
- [x] 자동 테스트 25개 (가짜 응답으로 처리 흐름 검증)
- [x] 마이크 + VAD 실제 발화 검출 확인 (`scripts/mic_vad.py`)
- [x] 데모 페이지에서 텍스트 입력으로 상품 선택 확인
- [ ] 데모 페이지에서 음성 입력으로 상품 선택 확인
- [ ] 모호한 상품 지칭 시 되묻기
- [ ] 실제 FE 화면에 연결
- [ ] 실시간 VAD 스트리밍 (최종 발표)
