from __future__ import annotations

from textwrap import shorten
from uuid import uuid4
from typing import Any
import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from ..core.config import settings
from ..dependencies import elastic_client, vertex_client
from ..core.metrics import SEARCH_SOURCE_COUNTER
from ..schemas.chat import (
    ActionRequest,
    ActionResponse,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    RetrievalSource,
)
from ..services.slack_client import post_slack_update
from ..services.workflows import suggest_follow_up

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


_FILTER_KEYWORDS: list[tuple[set[str], list[str]]] = [
    ({"sev", "incident", "ticket", "outage"}, ["ticket", "incident", "sev"]),
    ({"policy", "procedure", "byod", "compliance"}, ["policy", "procedure", "compliance"]),
    ({"playbook", "runbook", "remediation"}, ["playbook", "runbook", "remediation"]),
    ({"postmortem", "rca"}, ["postmortem", "rca"]),
    ({"chat", "transcript"}, ["chat", "conversation"]),
]


def _resolve_session_id(session_id: str | None) -> str:
    return session_id or f"session-{uuid4()}"


def _find_last_user_message(request: ChatRequest) -> ChatMessage | None:
    return next((m for m in reversed(request.messages) if m.role == "user"), None)


def _infer_filters(query: str) -> dict[str, list[str]]:
    lowered = query.lower()
    matched_tags: set[str] = set()
    for keywords, tags in _FILTER_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            matched_tags.update(tags)
    if not matched_tags:
        return {}
    return {"tags": sorted(matched_tags)}


async def _gather_references(
    query: str,
    locale: str | None = None,
) -> tuple[list[RetrievalSource], str, list[dict[str, Any]]]:
    if not elastic_client.enabled:
        return [], "", []

    filters = _infer_filters(query)
    hits = await elastic_client.semantic_search(
        query,
        filters=filters or None,
        locale=locale,
    )
    hits = await elastic_client.rerank(query, hits)

    references: list[RetrievalSource] = []
    context_lines: list[str] = []

    logger.info(
        "elastic_query_completed",
        extra={
            "query": query,
            "hit_count": len(hits),
            "indices": sorted({hit.get("_index", "unknown") for hit in hits}),
        },
    )

    for idx, hit in enumerate(hits[: settings.max_context_chunks], start=1):
        source = hit.get("_source", {})
        doc_id = hit.get("_id", f"doc-{idx}")
        title = source.get("title") or shorten(source.get("content", ""), width=80, placeholder="...")
        snippet = source.get("summary") or shorten(source.get("content", ""), width=220, placeholder="...")
        uri = source.get("uri") or source.get("link")
        score = hit.get("_rerank", {}).get("relevance_score") or hit.get("_score")

        SEARCH_SOURCE_COUNTER.labels(index=hit.get("_index", "unknown")).inc()

        references.append(
            RetrievalSource(
                id=doc_id,
                title=title or "Untitled",
                snippet=snippet,
                uri=uri,
                score=score,
            )
        )

        metadata_fields: list[tuple[str, str]] = [
            ("severity", "Severity"),
            ("priority", "Priority"),
            ("status", "Status"),
            ("owner", "Owner"),
            ("assigned_to", "Assignee"),
            ("category", "Category"),
            ("service", "Service"),
        ]
        metadata: dict[str, str] = {}
        for field, label in metadata_fields:
            value = source.get(field)
            if value:
                if isinstance(value, (list, tuple, set)):
                    value = ", ".join(str(item) for item in value if item)
                metadata[label] = str(value)

        tags = source.get("tags")
        if tags:
            if isinstance(tags, (list, tuple, set)):
                tag_str = ", ".join(str(tag) for tag in tags if tag)
            else:
                tag_str = str(tags)
            if tag_str:
                metadata["Tags"] = tag_str

        references.append(
            RetrievalSource(
                id=doc_id,
                title=title or "Untitled",
                snippet=snippet,
                uri=uri,
                score=score,
                metadata=metadata,
            )
        )

        metadata_line = "; ".join(f"{key}: {value}" for key, value in metadata.items())
        context_entry = [
            f"[{idx}] {references[-1].title}",
            f"Snippet: {references[-1].snippet or 'N/A'}",
        ]
        if metadata_line:
            context_entry.append(f"Metadata: {metadata_line}")
        context_entry.append(f"Source: {uri or doc_id}")
        context_lines.append("\n".join(context_entry))

    return references, "\n\n".join(context_lines), hits


def _build_system_prompt() -> str:
    return (
        "You are EverydayElastic, an enterprise IT and operations copilot. "
        "Use the retrieved tickets, policies, playbooks, and chat transcripts to provide concise, "
        "actionable incident triage and operational guidance. Cite sources inline using [#]. "
        "When analyzing incidents, highlight severity, affected services, owners, and next steps. "
        "Recommend follow-up actions (e.g., create Jira task, notify Slack channel, review policy) when appropriate. "
        "If context is insufficient, explicitly state what additional data is needed."
    )


async def _generate_answer(user_question: str, context: str, locale: str | None = None) -> str:
    if not vertex_client.enabled:
        return (
            "Vertex AI isn’t configured yet, so I can’t draft a full triage response. "
            "Use the retrieved context snippets for manual follow-up in the meantime."
        )

    prompt = (
        "Context documents:\n"
        f"{context or 'No external documents available.'}\n\n"
        "Task: Act as an IT/ops analyst. Provide an answer with citations such as [1], [2], "
        "highlighting current status, relevant runbooks, and recommended next actions.\n"
        f"User question: {user_question}"
    )

    try:
        return await vertex_client.generate_response(
            _build_system_prompt(),
            prompt,
            locale=locale,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Vertex AI generation failed")
        raise HTTPException(status_code=502, detail=f"Vertex AI generation failed: {exc}") from exc


@router.post("/completions", response_model=ChatResponse)
async def create_chat_completion(request: ChatRequest) -> ChatResponse:
    """Generate a chat completion with retrieval-augmented generation.
    
    Args:
        request: Chat request containing messages and optional session_id
        
    Returns:
        ChatResponse with assistant reply, sources, and follow-up actions
        
    Raises:
        HTTPException: If validation fails or generation errors occur
    """
    session_id = _resolve_session_id(request.session_id)
    
    logger.info(
        "chat_completion_request",
        extra={
            "session_id": session_id,
            "message_count": len(request.messages),
            "locale": request.locale,
        },
    )

    last_user = _find_last_user_message(request)
    if last_user is None:
        logger.warning("No user message found in request")
        reply = ChatMessage(role="assistant", content="How can I help you today?")
        return ChatResponse(session_id=session_id, reply=reply)

    try:
        locale = request.locale
        references, context, hits = await _gather_references(last_user.content, locale)
        answer = await _generate_answer(last_user.content, context, locale)
        follow_ups = []
        if references and elastic_client.enabled and hits:
            follow_ups = await suggest_follow_up(elastic_client, last_user.content, hits)

        reply = ChatMessage(role="assistant", content=answer)
        source_labels = [ref.uri or ref.id for ref in references]
        
        logger.info(
            "chat_completion_success",
            extra={
                "session_id": session_id,
                "sources_count": len(references),
                "follow_ups_count": len(follow_ups),
            },
        )

        return ChatResponse(
            session_id=session_id,
            reply=reply,
            sources=source_labels,
            references=references,
            follow_ups=follow_ups,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error in chat completion")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your request.",
        ) from exc


@router.post("/actions", response_model=ActionResponse)
async def execute_follow_up(action_request: ActionRequest) -> ActionResponse:
    """Execute a follow-up action from the copilot suggestion.
    
    Args:
        action_request: Action request with type and payload
        
    Returns:
        ActionResponse indicating success or failure
        
    Raises:
        HTTPException: If action execution fails
    """
    action = action_request.action
    payload = action_request.payload
    
    logger.info(
        "action_request",
        extra={
            "action": action,
            "payload_keys": list(payload.keys()),
        },
    )

    try:
        if action == "slack_webhook":
            await post_slack_update(payload)
            logger.info("slack_webhook_completed")
            return ActionResponse(status="ok", message="Slack update sent successfully")
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Action {action} failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Action {action} failed: {str(exc)}",
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported action '{action}'",
    )
