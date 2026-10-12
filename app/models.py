"""클래스도의 DTO: ScreenContext, VoiceCommand, VoiceResponse."""
from typing import Any

from pydantic import BaseModel, Field


class ScreenContext(BaseModel):
    """FE가 음성 요청과 함께 보내는 '지금 화면' 정보.

    LLM은 이 정보 안에서만 고르게 한다 (예: 화면에 없는 tourId를 만들어내지 않게).
    """
    screen: str = "list"                      # list | detail | configure | checkout
    tours: list[dict[str, Any]] = Field(default_factory=list)
    # tours 예: [{"tourId": 3, "title": "발리 허니문 5일", "theme": "HONEYMOON", "price": 1890000}]
    # 화면에 보이는 순서대로 보낸다 → "두 번째 거" = tours[1]
    availableTourLevels: list[str] = Field(default_factory=list)  # 예: ["GRAND", "PREMIUM"]
    drinkOptions: list[dict[str, Any]] = Field(default_factory=list)  # 예: [{"optionId": 1, "name": "샴페인"}]
    pendingAction: str | None = None          # 직전 응답에서 확인을 기다리던 action


class VoiceCommand(BaseModel):
    action: str
    params: dict[str, Any] = Field(default_factory=dict)


class VoiceResponse(BaseModel):
    recognizedText: str
    commands: list[VoiceCommand] = Field(default_factory=list)
    pending: dict[str, Any] = Field(default_factory=dict)  # 확인이 필요한 명령 (예: checkout)
