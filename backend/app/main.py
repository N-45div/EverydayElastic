from time import time

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

from .core.logging_config import setup_logging
from .core.metrics import REQUEST_LATENCY

from .api.routes import router as chat_router
from .dependencies import (
    configure_tracing,
    elastic_client,
    lifespan,
    vertex_client,
)

setup_logging()


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time()
        response = await call_next(request)
        duration = time() - start
        REQUEST_LATENCY.labels(
            path=request.url.path,
            method=request.method,
            status=response.status_code,
        ).observe(duration)
        return response


app = FastAPI(title="EverydayElastic API", version="0.1.0", lifespan=lifespan)
configure_tracing(app)
app.add_middleware(MetricsMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://localhost:3000",
        # Allow Cloud Run frontend deployments
        "https://everydayelastic-classi16-dztgcxd3oq-uc.a.run.app",
        "https://everyday-elastic.vercel.app"
    ],
    allow_origin_regex=r"https://.*\.run\.app",  # Allow all Cloud Run domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(chat_router)


@app.get("/metrics")
def metrics_endpoint() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/integrations/status")
async def integrations_status() -> dict[str, dict[str, str]]:
    from .core.config import settings
    
    elastic_status = {"status": "disabled"}
    if elastic_client.enabled:
        health = await elastic_client.health()
        elastic_status = {
            "status": health.get("status", "unknown"),
            "cluster_name": health.get("cluster_name", "unknown"),
        }

    vertex_status = {"status": "disabled"}
    if vertex_client.enabled:
        vertex_status = {"status": "enabled", **vertex_client.metadata()}
    
    slack_status = {"status": "disabled"}
    if settings.slack_access_token:
        slack_status = {
            "status": "enabled",
            "method": "web_api",
            "channel": settings.default_slack_channel,
        }
    elif settings.slack_webhook_url:
        slack_status = {
            "status": "enabled",
            "method": "webhook",
        }

    return {
        "elastic": elastic_status,
        "vertex_ai": vertex_status,
        "slack": slack_status,
    }
