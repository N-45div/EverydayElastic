from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp

from ..core.config import settings

logger = logging.getLogger(__name__)


async def call_jira_webhook(payload: dict[str, Any]) -> None:
    """Send a dry-run Jira webhook call (logs if URL missing)."""
    if not settings.jira_webhook_url:
        logger.info("[Dry-Run] JIRA webhook payload: %s", json.dumps(payload))
        return

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(settings.jira_webhook_url, json=payload, timeout=15) as response:
                body = await response.text()
                logger.info("JIRA webhook responded %s: %s", response.status, body)
        except Exception as exc:  # noqa: BLE001
            logger.warning("JIRA webhook call failed: %s", exc)
