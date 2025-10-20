from __future__ import annotations

from prometheus_client import Counter, Histogram

REQUEST_LATENCY = Histogram(
    "everydayelastic_request_latency_seconds",
    "Latency of FastAPI requests",
    labelnames=("path", "method", "status"),
)

SEARCH_SOURCE_COUNTER = Counter(
    "everydayelastic_search_sources_total",
    "Count of sources returned from Elastic",
    labelnames=("index",),
)
