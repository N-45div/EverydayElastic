from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1, max_length=10000)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Content cannot be empty or whitespace only")
        return v


class ChatRequest(BaseModel):
    session_id: str | None = None
    messages: list[ChatMessage] = Field(..., min_length=1, max_length=50)
    locale: str | None = Field(None, pattern=r"^[a-z]{2}-[A-Z]{2}$")

    @field_validator("locale")
    @classmethod
    def validate_locale(cls, v: str | None) -> str | None:
        if v is not None:
            allowed_locales = {"en-US", "es-ES", "fr-FR"}
            if v not in allowed_locales:
                raise ValueError(f"Locale must be one of {allowed_locales}")
        return v


class RetrievalSource(BaseModel):
    id: str
    title: str
    snippet: str | None = None
    uri: str | None = None
    score: float | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class FollowUpAction(BaseModel):
    label: str
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    session_id: str
    reply: ChatMessage
    sources: list[str] = Field(default_factory=list)
    references: list[RetrievalSource] = Field(default_factory=list)
    follow_ups: list[FollowUpAction] = Field(default_factory=list)


class ActionRequest(BaseModel):
    action: str = Field(..., min_length=1, max_length=100)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        allowed_actions = {"jira_webhook", "slack_webhook", "review_ticket", "manual_review"}
        if v not in allowed_actions:
            raise ValueError(f"Action must be one of {allowed_actions}")
        return v


class ActionResponse(BaseModel):
    status: str
    message: str

