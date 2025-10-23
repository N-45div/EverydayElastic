from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp

from ..core.config import settings

logger = logging.getLogger(__name__)

# In-memory cache for refreshed tokens (access + refresh)
_cached_access_token: str | None = None
_cached_refresh_token: str | None = None
_token_expires_at: datetime | None = None


async def _refresh_slack_token() -> str:
    """Refresh the Slack access token using the refresh token.
    
    Returns:
        New access token
        
    Raises:
        Exception: If token refresh fails
    """
    global _cached_access_token, _token_expires_at
    
    # Prefer the most recent refresh token if we have rotated once already
    global _cached_refresh_token
    effective_refresh_token = _cached_refresh_token or settings.slack_refresh_token
    if not effective_refresh_token:
        raise Exception("No refresh token configured")
    
    logger.info("Refreshing Slack access token...")
    
    async with aiohttp.ClientSession() as session:
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": effective_refresh_token,
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
                # Capture new refresh token if provided (Slack rotates it)
                new_refresh = data.get("refresh_token")
                if new_refresh:
                    _cached_refresh_token = new_refresh
                
                # Cache the token for ~11h (safe margin before 12h expiry)
                expires_in = data.get("expires_in")
                ttl = int(expires_in) if isinstance(expires_in, int) else 43200  # 12h default
                safe_ttl = max(0, ttl - 3600)  # refresh 1h early
                _cached_access_token = new_token
                _token_expires_at = datetime.utcnow() + timedelta(seconds=safe_ttl)
                
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
    
    # Prefer refresh path when possible (ensures expired tokens are replaced)
    if settings.slack_refresh_token or _cached_refresh_token:
        return await _refresh_slack_token()

    # Otherwise fall back to configured static token
    if settings.slack_access_token and not _cached_access_token:
        _cached_access_token = settings.slack_access_token
        _token_expires_at = datetime.utcnow() + timedelta(hours=11)
        return settings.slack_access_token
    
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
    
    # Prefer webhook posting when configured (demo-friendly and deterministic channel)
    if settings.slack_webhook_url:
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
        return

    # If no webhook, try Web API (requires tokens)
    if settings.slack_access_token or settings.slack_refresh_token:
        try:
            await post_slack_message_api(channel, message, ticket_info)
            return
        except Exception as exc:
            logger.warning("Slack Web API failed and no webhook configured: %s", exc)
            return

    # Nothing configured: dry-run
    logger.info("[Dry-Run] Slack payload (no webhook or token): %s", json.dumps(payload))
