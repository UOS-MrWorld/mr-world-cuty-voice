"""CommandValidator: LLM이 만든 명령을 화면 정보·Enum 기준으로 걸러낸다.

LLM은 가끔 없는 값을 지어낸다. 여기서 막아야 FE/BE에 이상한 값이 안 간다.
비즈니스 규칙(허니문 + CLASSIC 금지 등)은 BE가 검증한다 — 여기서는 '형식'만 본다.
"""
import re
from datetime import date

from .models import ScreenContext, VoiceCommand

UNKNOWN_MSG = "잘 못 알아들었어요. 다시 말씀해 주세요."
LEVEL_KO = {"CLASSIC": "클래식", "GRAND": "그랜드", "PREMIUM": "프리미엄"}


class CommandValidator:
    def __init__(self):
        self.allowedActions = ["search", "select", "configure", "next", "checkout",
                               "back", "summary", "confirm", "cancel", "unknown"]
        self.enumValues = {
            "theme": ["HONEYMOON", "HEALING", "GOLF", "TREKKING"],
            "tourLevel": ["CLASSIC", "GRAND", "PREMIUM"],
            "hotelGrade": ["THREE_STAR", "FOUR_STAR", "FIVE_STAR"],
            "mealType": ["LUNCH_BOX", "LOCAL_RESTAURANT", "FINE_DINING"],
            "transport": ["PREMIUM_CAR_2", "PREMIUM_VAN_10"],
        }

    def validate(self, commands: list[VoiceCommand], context: ScreenContext) -> list[VoiceCommand]:
        out = []
        for c in commands:
            checked = self._check(c, context)
            if checked:
                out.append(checked)
        if not out:  # 하나도 못 살리면 unknown 하나
            out = [VoiceCommand(action="unknown", params={"message": UNKNOWN_MSG})]
        return out

    def _check(self, c: VoiceCommand, ctx: ScreenContext) -> VoiceCommand | None:
        if c.action not in self.allowedActions:
            return None
        p = {k: v for k, v in c.params.items() if v is not None}

        # Enum 값 확인: 모르는 값은 버린다
        for key, allowed in self.enumValues.items():
            if key in p and p[key] not in allowed:
                p.pop(key)

        if c.action == "search":
            if "maxPrice" in p and (not isinstance(p["maxPrice"], int) or p["maxPrice"] <= 0):
                p.pop("maxPrice")
            p = {k: v for k, v in p.items()
                 if k in ("theme", "keyword", "maxPrice", "startDateFrom", "startDateTo")}

        elif c.action == "select":
            # 연동 핵심: 화면에 실제로 있는 상품만 고를 수 있다
            ids = [t.get("tourId") for t in ctx.tours]
            if p.get("tourId") not in ids:
                return VoiceCommand(action="unknown",
                                    params={"message": "어떤 상품인지 다시 말씀해 주세요. 예: 두 번째 거 보여줘"})
            p = {"tourId": p["tourId"]}

        elif c.action == "configure":
            blockedLevel = None
            if ctx.availableTourLevels and p.get("tourLevel") not in (None, *ctx.availableTourLevels):
                blockedLevel = p.pop("tourLevel")
            gc = p.get("guestCount")
            if gc is not None and not (isinstance(gc, int) and 1 <= gc <= 10):
                p.pop("guestCount")
            if "drinkOptions" in p:
                ok_ids = {d.get("optionId") for d in ctx.drinkOptions}
                p["drinkOptions"] = [d for d in p["drinkOptions"]
                                     if isinstance(d, dict) and d.get("optionId") in ok_ids
                                     and isinstance(d.get("quantity"), int) and d["quantity"] >= 0]
                if not p["drinkOptions"]:
                    p.pop("drinkOptions")
            if "departureDate" in p and not self._futureDate(p["departureDate"]):
                p.pop("departureDate")
            p = {k: v for k, v in p.items() if k in
                 ("tourLevel", "hotelGrade", "mealType", "transport", "guestCount", "drinkOptions", "departureDate")}
            if not p:
                if blockedLevel:  # 고를 수 없는 등급만 말한 경우: 이유를 알려준다
                    return VoiceCommand(action="unknown", params={
                        "message": f"이 상품은 {LEVEL_KO.get(blockedLevel, blockedLevel)} 등급을 고를 수 없어요. "
                                   f"{', '.join(LEVEL_KO.get(x, x) for x in ctx.availableTourLevels)} 중에서 골라 주세요."})
                return None

        elif c.action == "unknown":
            p = {"message": p.get("message") or UNKNOWN_MSG}
        else:
            p = {}
        return VoiceCommand(action=c.action, params=p)

    @staticmethod
    def _futureDate(value) -> bool:
        """"YYYY-MM-DD" 형식이고 오늘 이후인 실제 날짜만 통과."""
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return False
        try:
            return date.fromisoformat(value) > date.today()
        except ValueError:
            return False
