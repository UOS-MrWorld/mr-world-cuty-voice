import calendar
import json
import os
from datetime import date

from .models import ScreenContext, VoiceCommand

SYSTEM_PROMPT = """너는 여행 예약 서비스 Mr.CUTY의 음성 명령 해석기다.
고객이 한 말(한국어)과 지금 화면 정보를 보고, 실행할 명령을 JSON으로만 답한다.

출력 형식: {"commands": [{"action": "...", "params": {...}}]}
한 문장에 명령이 여러 개면 순서대로 여러 개를 넣는다.

action 종류와 params:
- search: 여행 상품 검색. params: theme, keyword, maxPrice, month
  - theme: HONEYMOON(허니문) / HEALING(효도·힐링) / GOLF(골프) / TREKKING(트레킹) / null
  - maxPrice: 원 단위 정수 ("100만원 이하" → 1000000) / null
  - month: 1~12 정수 ("10월에 가는" → 10) / null. 날짜는 월 단위로만 받는다
  - keyword: 여행지나 상품명 ("발리", "제주") / null
- select: 목록에서 상품 고르기. params: tourId
  - 반드시 화면 정보 tours 안의 tourId만 쓴다. tours는 화면에 보이는 순서다
  - "두 번째 거" → tours[1]의 tourId, "발리 거" → tourName에 발리가 들어간 상품
  - 어느 상품인지 확실하지 않으면 select 대신 unknown
- configure: 여행 구성 변경. params: tourLevel, hotelGrade, mealType, transport, guestCount, drinkOptions, departureDate
  - tourLevel: CLASSIC(클래식) / GRAND(그랜드) / PREMIUM(프리미엄)
  - hotelGrade: THREE_STAR / FOUR_STAR / FIVE_STAR ("5성급", "5등급 호텔" → FIVE_STAR)
  - mealType: LUNCH_BOX(도시락) / LOCAL_RESTAURANT(현지 식당·현지식) / FINE_DINING(파인다이닝·고급 레스토랑·스테이크)
  - transport: PREMIUM_CAR_2(2인 전용 차량) / PREMIUM_VAN_10(10인승 차량·밴)
  - guestCount: 정수 ("두 명" → 2, "두 커플" → 4)
  - drinkOptions: [{"optionId": 정수, "quantity": 정수}] — 화면 정보 drinkOptions의 optionId만 쓴다. 빼달라고 하면 quantity 0
  - departureDate: 출발 희망일 "YYYY-MM-DD". 오늘 날짜(today)를 기준으로 계산 ("11월 20일" → 다가오는 11월 20일)
  - 말하지 않은 항목은 넣지 않는다
- next: 지금 화면의 다음 단계로 이동 ("다음", "옵션 고르러 갈게", "이대로 진행해줘"). params 없음
- checkout: 예약(신청) 화면으로 이동 ("이걸로 예약할게", "신청할게"). params 없음. 결제 실행은 절대 아니다
- back: 이전 화면. params 없음
- summary: 지금 선택한 구성과 금액 알려주기. params 없음
- confirm: 직전 질문에 "응/네/그래"로 동의. params 없음
- cancel: 직전 질문에 "아니/취소"로 거절. params 없음
- unknown: 알아들을 수 없거나 서비스와 관계없는 말. params: message (다시 말해달라는 짧은 한국어 문장)

규칙 판단(허니문은 클래식 불가 등)은 하지 말고 들은 그대로 변환한다. 그 검증은 서버가 한다."""


class CommandParser:
    def __init__(self, groqClient=None, model: str = "openai/gpt-oss-120b"):
        if groqClient is None:
            from groq import Groq
            groqClient = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.groqClient = groqClient
        self.model = model

    def parse(self, text: str, context: ScreenContext) -> list[VoiceCommand]:
        user = json.dumps({"text": text, "today": date.today().isoformat(), "context": context.model_dump()},
                          ensure_ascii=False)
        res = self.groqClient.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": SYSTEM_PROMPT},
                      {"role": "user", "content": user}],
            response_format={"type": "json_object"},
            temperature=0,
            reasoning_effort=os.getenv("LLM_REASONING_EFFORT", "low"),
            include_reasoning=False,
        )
        try:
            raw = json.loads(res.choices[0].message.content)
            commands = [VoiceCommand(**c) for c in raw.get("commands", [])]
        except (json.JSONDecodeError, TypeError, ValueError):
            commands = []
        for c in commands:
            if c.action == "search" and c.params.get("month"):
                start, end = self.convertMonth(str(c.params.pop("month")))
                c.params["startDateFrom"], c.params["startDateTo"] = start, end
        return commands

    def convertMonth(self, month: str, today: date | None = None) -> tuple:
        today = today or date.today()
        m = int(month)
        year = today.year + (1 if m < today.month else 0)
        last = calendar.monthrange(year, m)[1]
        return f"{year}-{m:02d}-01", f"{year}-{m:02d}-{last:02d}"
