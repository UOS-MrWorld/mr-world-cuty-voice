# 음성인식 구조 설계

## 1. 전체 구조

```
[FE 브라우저]  🎤 녹음 (16kHz 모노 WAV) + 지금 화면 정보(ScreenContext)
     │  POST /api/v1/voice/command  (multipart: audio, context)
     ▼
┌─────────────────── Voice AI Server (Python, FastAPI) ───────────────────┐
│ VoiceController.handleVoiceCommand(audio, context)                      │
│   ① VadDetector.extractSpeech   Silero VAD — 말한 구간만 잘라냄          │
│   ② SttClient.transcribe        Groq whisper-large-v3-turbo — 음성→텍스트 │
│   ③ CommandParser.parse         Groq gpt-oss-120b — 텍스트+화면→명령 JSON │
│   ④ CommandValidator.validate   화면에 있는 값·Enum만 통과               │
└──────────────────────────────────────────────────────────────────────────┘
     │  VoiceResponse { recognizedText, commands[], pending }
     ▼
[FE] 명령대로 화면 이동 / BE API 호출   →   [BE] 비즈니스 규칙 검증
```

클래스 이름과 메서드는 StarUML의 **Voice AI Server 클래스도**와 같다.

| 클래스 | 메서드 | 역할 |
|---|---|---|
| VoiceController | handleVoiceCommand(audio, context) → VoiceResponse | ①~④ 순서 실행, 확인 필요 명령은 pending으로 |
| VadDetector | extractSpeech(audio) → bytes | 무음 제거. 말이 없으면 STT를 호출하지 않음 |
| SttClient | transcribe(speech) → str | 여행 용어 프롬프트로 오인식 줄임 |
| CommandParser | parse(text, context) → list<VoiceCommand>, convertMonth(month) | LLM JSON 모드, "10월" → 10/01~10/31 |
| CommandValidator | validate(commands, context) → list<VoiceCommand> | 없는 tourId·Enum·옵션 제거 |
| ScreenContext / VoiceCommand / VoiceResponse | — | 요청·응답 DTO |

## 2. 화면 정보 (ScreenContext)

LLM이 **화면에 실제로 있는 것 중에서만** 고르게 하려고 FE가 매 요청마다 보낸다.

```json
{
  "screen": "list",
  "tours": [
    { "tourId": 11, "tourName": "발리 허니문 5일", "theme": "HONEYMOON", "price": 1890000 },
    { "tourId": 23, "tourName": "제주 효도 힐링 3일", "theme": "HEALING", "price": 690000 }
  ],
  "availableTourLevels": ["GRAND", "PREMIUM"],
  "drinkOptions": [{ "optionId": 1, "name": "샴페인" }],
  "pendingAction": null
}
```

- `tours`는 **화면에 보이는 순서대로** 보낸다 → "두 번째 거" = `tours[1]`
- `pendingAction`: 직전 응답의 `pending.action`을 그대로 돌려보낸다 ("응"이라고 하면 실행)

## 3. 명령 (VoiceResponse)

```json
{ "recognizedText": "두 번째 거 보여줘",
  "commands": [{ "action": "select", "params": { "tourId": 23 } }],
  "pending": {} }
```

| action | params | FE 동작 |
|---|---|---|
| search | theme, keyword, maxPrice, startDateFrom, startDateTo | 목록 필터 적용 |
| select | tourId | 상품 상세로 이동 |
| configure | tourLevel, hotelGrade, mealType, transport, guestCount, drinkOptions | 구성 화면 값 변경 |
| checkout | — | 신청 화면으로 이동 (**항상 pending으로 먼저 확인**) |
| back | — | 이전 화면 |
| summary | — | 현재 구성·금액 안내 |
| cancel | — | 확인 창 닫기 |
| unknown | message | 안내 문구 표시 |

- Enum은 BE와 같다: Theme(HONEYMOON/HEALING/GOLF/TREKKING), TourLevel(CLASSIC/GRAND/PREMIUM), HotelGrade, MealType, Transport
- 한 문장에 명령이 여러 개면 순서대로 여러 개 ("골프 여행 찾아서 첫 번째 거 보여줘")
- 말하지 않은 항목은 params에 없다 = 변경 없음

## 4. 안전장치

| 상황 | 처리 |
|---|---|
| 결제 | 음성으로 실행 불가. checkout(신청 화면 이동)까지만, 그것도 한 번 더 확인 |
| 화면에 없는 상품 ("다섯 번째 거" — 4개뿐) | Validator가 select를 unknown으로 바꿈 |
| LLM이 없는 Enum·옵션을 만듦 | 해당 값만 버림 |
| 말소리 없음 | VAD에서 끝냄 (STT 비용 0) |
| LLM 응답이 JSON이 아님 | unknown |
| 허니문 + CLASSIC 같은 규칙 위반 | AI는 그대로 전달, **BE가 400으로 검증**, FE가 안내 |

## 5. 결정 사항 / 남은 일

- [x] 화면별 context 형식
- [x] action별 FE 동작
- [x] 녹음 방식: M2는 버튼 녹음 → WAV 전송. 최종은 실시간 VAD 스트리밍 검토
- [x] AI 서버 주소 `:8000`, CORS는 `.env`의 `CORS_ORIGINS`
- [ ] FE 실제 화면(/tours, /tours/:id/configure)에 붙이기 — 지금 FE 음성 버튼은 파형 시각화만 함
