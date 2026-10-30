# 음성 AI 서버 API 명세

- Base URL: 로컬 `http://localhost:8000/api/v1` (배포 주소는 배포 후 추가)
- 인증: 없음 (음성 → 명령 변환만 하고, 상품·예약 데이터는 다루지 않음. 실제 처리와 권한 검증은 BE)
- 에러 응답은 팀 API 명세서의 **공통 에러 응답 형식**을 따른다.

## POST /api/v1/voice/command — 음성 명령 변환

`multipart/form-data`

| key | 설명 | 타입 | Nullable | 예시 |
|---|---|---|---|---|
| audio | 녹음 파일 (16kHz·모노·16bit WAV, 10MB 이하) | File | N | speech.wav |
| context | 지금 화면 정보 (ScreenContext JSON 문자열) | String | Y (기본 `{}`) | 아래 참고 |

```json
{
  "screen": "list",
  "tours": [{ "tourId": "bali", "tourName": "발리 허니문 5박 7일", "theme": "허니문", "price": 1890000 }],
  "availableTourLevels": ["GRAND", "PREMIUM"],
  "drinkOptions": [{ "optionId": 1, "name": "샴페인" }],
  "pendingAction": null
}
```

Response 200

```json
{
  "recognizedText": "두 번째 거 보여줘",
  "commands": [{ "action": "select", "params": { "tourId": "kyoto" } }],
  "pending": {}
}
```

action: `search` · `select` · `configure` · `next` · `checkout`(항상 pending으로 먼저 확인) · `back` · `summary` · `cancel` · `unknown`
— 각 params는 [pipeline.md](pipeline.md) 3장 참고. 알아듣지 못한 경우도 에러가 아니라 200 + `unknown`으로 응답한다.

## POST /api/v1/voice/text — 문장으로 명령 변환 (개발·검증용)

`application/json` — `{ "text": "두 번째 거 보여줘", "context": { ... } }` → 응답은 위와 같다. (VAD·STT 생략)

## GET /health — 상태 확인

`{ "status": "ok" }` — Groq를 호출하지 않는다. 배포 서버 깨우기(keep-alive)에 사용.

## 에러 응답

```json
{
  "status": 400,
  "code": "INVALID_INPUT",
  "message": "context 형식이 올바르지 않습니다. ScreenContext JSON 문자열을 보내 주세요.",
  "path": "/api/v1/voice/command",
  "timestamp": "2026-10-30T14:40:00"
}
```

| status | code | 언제 |
|---|---|---|
| 400 | INVALID_INPUT | audio 누락·빈 파일·10MB 초과, WAV 형식 아님, context JSON 오류, text 비어 있음 |
| 404 | RESOURCE_NOT_FOUND | 없는 경로 |
| 500 | INTERNAL_SERVER_ERROR | 예상하지 못한 서버 오류 |
| 503 | VOICE_SERVICE_UNAVAILABLE | 외부 음성 모델(Groq) 연결 실패·요청 한도 초과 |
