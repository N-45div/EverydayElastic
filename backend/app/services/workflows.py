from __future__ import annotations

import logging
from typing import Any

from ..core.config import settings
from ..services.elastic import ElasticClient
from ..schemas.chat import FollowUpAction

logger = logging.getLogger(__name__)


def should_trigger_slack(warning_tags: set[str]) -> bool:
    return bool({"sev", "incident"} & warning_tags)


async def suggest_follow_up(elastic: ElasticClient, query: str, hits: list[dict[str, Any]]) -> list[FollowUpAction]:
    suggestions: list[FollowUpAction] = []
    top_ticket = next((hit for hit in hits if "ticket" in hit.get("_source", {}).get("tags", [])), None)
    
    # Only suggest Slack action for incidents
    if top_ticket and settings.slack_webhook_url:
        ticket_source = top_ticket.get("_source", {})
        if should_trigger_slack(set(ticket_source.get("tags", []))):
            channel = settings.default_slack_channel
            suggestions.append(
                FollowUpAction(
                    label=f"📤 Send to {channel}",
                    action="slack_webhook",
                    payload={
                        "channel": channel,
                        "message": f"🚨 *Incident Alert:* {ticket_source.get('title', 'Unknown')}\n\n{ticket_source.get('content', '')[:300]}...",
                        "ticket_info": {
                            "severity": ticket_source.get("severity"),
                            "status": ticket_source.get("status"),
                            "owner": ticket_source.get("owner"),
                            "service": ticket_source.get("service"),
                        },
                    },
                )
            )
    
    return suggestions
