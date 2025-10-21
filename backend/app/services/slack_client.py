from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp

from ..core.config import settings

logger = logging.getLogger(__name__)

# In-memory cache for refreshed token (expires after 11 hours to be safe)
_cached_access_token: str | None = None
_token_expires_at: datetime | None = None


async def _refresh_slack_token() -> str:
    """Refresh the Slack access token using the refresh token.
    
    Returns:
        New access token
        
    Raises:
        Exception: If token refresh fails
    """
    global _cached_access_token, _token_expires_at
    
    if not settings.slack_refresh_token:
        raise Exception("No refresh token configured")
    
    logger.info("Refreshing Slack access token...")
    
    async with aiohttp.ClientSession() as session:
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": settings.slack_refresh_token,
            "client_id": settings.slack_client_id,
            "client_secret": settings.slack_client_secret,
        }
        
        try:
            async with session.post(
                "https://slack.com/api/oauth.v2.access",
                data=payload,
                timeout=10
            ) as response:
                data = await response.json()
                
                if not data.get("ok"):
                    error = data.get("error", "unknown")
                    logger.error("Token refresh failed: %s", error)
                    raise Exception(f"Token refresh failed: {error}")
                
                new_token = data.get("access_token")
                if not new_token:
                    raise Exception("No access token in refresh response")
                
                # Cache the token for 11 hours (safe margin before 12h expiry)
                _cached_access_token = new_token
                _token_expires_at = datetime.utcnow() + timedelta(hours=11)
                
                logger.info("Slack access token refreshed successfully (expires in 11h)")
                return new_token
                
        except Exception as exc:
            logger.exception("Failed to refresh Slack token")
            raise


async def _get_valid_access_token() -> str:
    """Get a valid access token, refreshing if necessary.
    
    Returns:
        Valid access token
        
    Raises:
        Exception: If no token available or refresh fails
    """
    global _cached_access_token, _token_expires_at
    
    # Use cached token if still valid
    if _cached_access_token and _token_expires_at:
        if datetime.utcnow() < _token_expires_at:
            return _cached_access_token
        logger.info("Cached token expired, refreshing...")
    
    # Use configured token if available and no cached token
    if settings.slack_access_token and not _cached_access_token:
        # Initialize cache with configured token (assume fresh for 11 hours)
        _cached_access_token = settings.slack_access_token
        _token_expires_at = datetime.utcnow() + timedelta(hours=11)
        return settings.slack_access_token
    
    # Refresh token if we have a refresh token
    if settings.slack_refresh_token:
        return await _refresh_slack_token()
    
    raise Exception("No valid Slack token available and no refresh token configured")


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
    
    Automatically handles token expiry and refresh.
    
    Args:
        channel: Channel name (with or without #) or channel ID
        message: Message text
        ticket_info: Optional ticket details for formatting
        
    Returns:
        API response data
        
    Raises:
        Exception: If API call fails
    """
    if not settings.slack_access_token and not settings.slack_refresh_token:
        logger.info("[Dry-Run] Slack API message to %s: %s", channel, message)
        return {"ok": True, "dry_run": True}
    
    # Clean channel name
    channel = channel.lstrip("#")
    
    payload = _format_slack_message(message, ticket_info)
    payload["channel"] = channel
    
    # Try with current token, refresh and retry if expired
    for attempt in range(2):
        try:
            access_token = await _get_valid_access_token()
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://slack.com/api/chat.postMessage",
                    json=payload,
                    headers=headers,
                    timeout=10
                ) as response:
                    data = await response.json()
                    
                    # Handle token expiry error
                    if not data.get("ok"):
                        error = data.get("error")
                        
                        # If token is expired/invalid and this is first attempt, refresh and retry
                        if error in ("token_expired", "invalid_auth", "token_revoked") and attempt == 0:
                            logger.warning("Token error (%s), refreshing and retrying...", error)
                            # Force refresh by clearing cache
                            global _cached_access_token, _token_expires_at
                            _cached_access_token = None
                            _token_expires_at = None
                            continue  # Retry loop
                        
                        logger.error("Slack API error: %s", error)
                        raise Exception(f"Slack API error: {error}")
                    
                    logger.info("Slack message posted to %s successfully", channel)
                    return data
                    
        except Exception as exc:
            if attempt == 1:  # Last attempt
                logger.error("Slack API call failed after retry: %s", exc)
                raise
            logger.warning("Slack API call failed, will retry: %s", exc)


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
