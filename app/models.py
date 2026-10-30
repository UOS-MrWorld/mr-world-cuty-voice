from typing import Any

from pydantic import BaseModel, Field


class ScreenContext(BaseModel):
    screen: str = "list"
    tours: list[dict[str, Any]] = Field(default_factory=list)
    availableTourLevels: list[str] = Field(default_factory=list)
    drinkOptions: list[dict[str, Any]] = Field(default_factory=list)
    pendingAction: str | None = None


class VoiceCommand(BaseModel):
    action: str
    params: dict[str, Any] = Field(default_factory=dict)


class VoiceResponse(BaseModel):
    recognizedText: str
    commands: list[VoiceCommand] = Field(default_factory=list)
    pending: dict[str, Any] = Field(default_factory=dict)
