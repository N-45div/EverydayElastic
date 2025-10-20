from __future__ import annotations

import asyncio
from typing import Any

import vertexai
from vertexai.generative_models import Content, GenerativeModel, GenerationConfig, Part

from ..core.config import settings


class VertexAIClient:
    def __init__(
        self,
        project_id: str | None,
        location: str,
        model_name: str,
    ) -> None:
        self._project_id = project_id
        self._location = location
        self._model_name = model_name
        self._initialized = False
        self._model: GenerativeModel | None = None

    @property
    def enabled(self) -> bool:
        return bool(self._project_id)

    def ensure_init(self) -> None:
        if not self.enabled:
            raise RuntimeError("Vertex AI project ID not configured")
        if not self._initialized:
            vertexai.init(project=self._project_id, location=self._location)
            self._initialized = True

    def ensure_model(self) -> GenerativeModel:
        self.ensure_init()
        if self._model is None:
            self._model = GenerativeModel(self._model_name)
        return self._model

    async def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.2,
        max_output_tokens: int = 768,
        locale: str | None = None,
    ) -> str:
        if not self.enabled:
            raise RuntimeError("Vertex AI client is disabled")
        model = self.ensure_model()

        def _invoke() -> str:
            instructions = system_prompt
            if locale:
                instructions = (
                    f"{system_prompt}\n\n"
                    f"Respond in the locale '{locale}'. When citing sources, keep citation markers as [1], [2]. "
                    "Translate relevant snippets from the context if needed so the final answer is coherent in the requested locale."
                )
            merged_prompt = (
                f"{instructions}\n\n"
                f"User request:\n{user_prompt}"
            )
            contents = [
                Content(role="user", parts=[Part.from_text(merged_prompt)]),
            ]
            config_kwargs: dict[str, Any] = {
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
            }
            response = model.generate_content(
                contents,
                generation_config=GenerationConfig(**config_kwargs),
            )
            return self._extract_text(response)

        return await asyncio.to_thread(_invoke)

    @staticmethod
    def _extract_text(response: Any) -> str:
        if response is None:
            return ""
        # Newer SDKs expose `.text`; otherwise inspect candidates.
        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()
        candidates = getattr(response, "candidates", []) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            if content and getattr(content, "parts", None):
                parts = content.parts
                fragments: list[str] = []
                for part in parts:
                    value = getattr(part, "text", None)
                    if isinstance(value, str):
                        fragments.append(value)
                combined = "".join(fragments).strip()
                if combined:
                    return combined
        return ""

    def metadata(self) -> dict[str, Any]:
        if not self.enabled:
            return {"status": "disabled"}
        return {
            "model": self._model_name,
            "location": self._location,
        }

    @classmethod
    def from_settings(cls) -> "VertexAIClient":
        return cls(
            project_id=settings.vertex_project_id,
            location=settings.vertex_location,
            model_name=settings.vertex_model,
        )
