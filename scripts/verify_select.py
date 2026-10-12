"""실제 Groq로 '여행상품 선택' 연동을 검증한다 (텍스트 → JSON 명령).

사용법: python scripts/verify_select.py
결과: 터미널 표 + docs/verification_result.md
.env에 GROQ_API_KEY가 있어야 한다.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv

load_dotenv()
from app.controller import VoiceController  # noqa: E402
from app.models import ScreenContext  # noqa: E402
from tests.fakes import SAMPLE_TOURS  # noqa: E402

LIST = ScreenContext(screen="list", tours=SAMPLE_TOURS)
CONFIG = ScreenContext(screen="configure", availableTourLevels=["GRAND", "PREMIUM"],
                       drinkOptions=[{"optionId": 1, "name": "샴페인"}, {"optionId": 2, "name": "커피"}])

# (발화, 화면, 기대 action 목록, 기대 params 일부)
CASES = [
    ("두 번째 거 보여줘", LIST, ["select"], {"tourId": 23}),
    ("첫 번째 상품 선택할게", LIST, ["select"], {"tourId": 11}),
    ("마지막 거로 할게", LIST, ["select"], {"tourId": 42}),
    ("발리 가는 거 보여줘", LIST, ["select"], {"tourId": 11}),
    ("골프 여행 상세 보여줘", LIST, ["select"], {"tourId": 37}),
    ("다섯 번째 거 보여줘", LIST, ["unknown"], {}),  # 4개뿐 → 막혀야 함
    ("10월에 가는 100만원 이하 효도 여행 찾아줘", LIST, ["search"], {"theme": "HEALING", "maxPrice": 1000000}),
    ("허니문 상품만 보여줘", LIST, ["search"], {"theme": "HONEYMOON"}),
    ("그랜드로 하고 5성급 호텔로 바꿔줘", CONFIG, ["configure"], {"tourLevel": "GRAND", "hotelGrade": "FIVE_STAR"}),
    ("두 명이요", CONFIG, ["configure"], {"guestCount": 2}),
    ("이걸로 예약할게", CONFIG, [], {}),  # checkout은 pending으로
    ("뒤로 가줘", LIST, ["back"], {}),
    ("다음 단계로 가줘", CONFIG, ["next"], {}),
    ("프리미엄으로 하고 커피 추가해줘", CONFIG, ["configure"], {"tourLevel": "PREMIUM", "drinkOptions": [{"optionId": 2, "quantity": 1}]}),
    ("11월 20일 출발로 해줘", CONFIG, ["configure"], {}),  # 날짜는 아래에서 따로 확인
    ("오늘 점심 뭐 먹지", LIST, ["unknown"], {}),
]


def main():
    ctrl = VoiceController(vad=object(), stt=object())  # 텍스트 검증이라 VAD·STT는 안 씀
    rows, ok_n = [], 0
    for text, ctx, want_actions, want_params in CASES:
        t0 = time.time()
        res = ctrl._fromText(text, ctx)
        ms = int((time.time() - t0) * 1000)
        actions = [c.action for c in res.commands]
        params = {k: v for c in res.commands for k, v in c.params.items()}
        ok = actions == want_actions and all(params.get(k) == v for k, v in want_params.items())
        if text == "11월 20일 출발로 해줘":
            ok = ok and str(params.get("departureDate", "")).endswith("-11-20")
        if text == "이걸로 예약할게":
            ok = res.pending.get("action") == "checkout"
        ok_n += ok
        got = "; ".join(f"{c.action} {c.params}" for c in res.commands) + (f" | pending {res.pending}" if res.pending else "")
        rows.append((("✅" if ok else "❌"), text, ctx.screen, got, ms))
        print(rows[-1])

    lines = ["# 여행상품 선택 연동 검증 결과", "",
             f"- 모델: STT 생략(텍스트 입력), LLM `{ctrl.parser.model}`",
             f"- 통과: **{ok_n} / {len(CASES)}**", "",
             "| 결과 | 발화 | 화면 | 변환된 명령 | 응답(ms) |", "|---|---|---|---|---|"]
    lines += [f"| {r[0]} | {r[1]} | {r[2]} | `{r[3]}` | {r[4]} |" for r in rows]
    out = os.path.join(os.path.dirname(__file__), "..", "docs", "verification_result.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\n통과 {ok_n}/{len(CASES)} → docs/verification_result.md")


if __name__ == "__main__":
    main()
