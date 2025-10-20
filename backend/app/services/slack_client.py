from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp

from ..core.config import settings

logger = logging.getLogger(__name__)


def _format_slack_message(message: str, ticket_info: dict[str, Any] | None = None) -> dict[str, Any]:
    """Format a rich Slack message with blocks for better presentation."""
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": message
            }
        }
    ]
    
    if ticket_info:
        fields = []
        if ticket_info.get("severity"):
            fields.append({
                "type": "mrkdwn",
                "text": f"*Severity:*\n{ticket_info['severity']}"
            })
        if ticket_info.get("status"):
            fields.append({
                "type": "mrkdwn",
                "text": f"*Status:*\n{ticket_info['status']}"
            })
        if ticket_info.get("owner"):
            fields.append({
                "type": "mrkdwn",
                "text": f"*Owner:*\n{ticket_info['owner']}"
            })
        
        if fields:
            blocks.append({
                "type": "section",
                "fields": fields
            })
    
    return {"blocks": blocks}


async def post_slack_message_api(channel: str, message: str, ticket_info: dict[str, Any] | None = None) -> dict[str, Any]:
    """Post a message to Slack using the Web API with rich formatting.
    
    Args:
        channel: Channel name (with or without #) or channel ID
        message: Message text
        ticket_info: Optional ticket details for formatting
        
    Returns:
        API response data
        
    Raises:
        Exception: If API call fails
    """
    if not settings.slack_access_token:
        logger.info("[Dry-Run] Slack API message to %s: %s", channel, message)
        return {"ok": True, "dry_run": True}
    
    # Clean channel name
    channel = channel.lstrip("#")
    
    payload = _format_slack_message(message, ticket_info)
    payload["channel"] = channel
    
    headers = {
        "Authorization": f"Bearer {settings.slack_access_token}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                "https://slack.com/api/chat.postMessage",
                json=payload,
                headers=headers,
                timeout=10
            ) as response:
                data = await response.json()
                if not data.get("ok"):
                    logger.error("Slack API error: %s", data.get("error"))
                    raise Exception(f"Slack API error: {data.get('error')}")
                logger.info("Slack message posted to %s successfully", channel)
                return data
        except Exception as exc:
            logger.error("Slack API call failed: %s", exc)
            raise


async def post_slack_update(payload: dict[str, Any]) -> None:
    """Send Slack update using Web API or webhook fallback.
    
    Args:
        payload: Must contain 'channel' and 'message'. Optional 'ticket_info'.
    """
    channel = payload.get("channel", settings.default_slack_channel)
    message = payload.get("message", "")
    ticket_info = payload.get("ticket_info")
    
    # Try Web API first (more powerful)
    if settings.slack_access_token:
        try:
            await post_slack_message_api(channel, message, ticket_info)
            return
        except Exception as exc:
            logger.warning("Slack Web API failed, falling back to webhook: %s", exc)
    
    # Fallback to webhook
    if not settings.slack_webhook_url:
        logger.info("[Dry-Run] Slack webhook payload: %s", json.dumps(payload))
        return

    webhook_payload = {"text": message}
    if ticket_info:
        webhook_payload["text"] = f"{message}\n\nDetails: {json.dumps(ticket_info, indent=2)}"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(settings.slack_webhook_url, json=webhook_payload, timeout=10) as response:
                body = await response.text()
                logger.info("Slack webhook responded %s: %s", response.status, body)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Slack webhook call failed: %s", exc)
