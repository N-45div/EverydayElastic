from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from .core.config import settings

from .services.elastic import ElasticClient
from .services.vertex import VertexAIClient


elastic_client = ElasticClient.from_settings()
vertex_client = VertexAIClient.from_settings()


def configure_tracing(app: FastAPI) -> None:
    if not settings.enable_tracing:
        return

    if getattr(app.state, "otel_tracing_enabled", False):
        return

    resource = Resource.create(
        {
            "service.name": settings.project_name,
            "deployment.environment": settings.environment,
        }
    )

    provider = TracerProvider(resource=resource)

    exporter_kwargs: dict[str, object] = {}
    if settings.otel_exporter_endpoint:
        exporter_kwargs["endpoint"] = settings.otel_exporter_endpoint
    if settings.otel_exporter_headers:
        raw_headers = settings.otel_exporter_headers
        header_map: dict[str, str] = {}
        if isinstance(raw_headers, dict):
            header_map = {str(k): str(v) for k, v in raw_headers.items()}
        else:
            entries = [entry.strip() for entry in str(raw_headers).split(",") if entry.strip()]
            for entry in entries:
                if "=" not in entry:
                    continue
                key, value = entry.split("=", 1)
                header_map[key.strip()] = value.strip()
        if header_map:
            exporter_kwargs["headers"] = header_map
    if settings.otel_exporter_insecure:
        exporter_kwargs["insecure"] = True

    span_exporter = OTLPSpanExporter(**exporter_kwargs)
    span_processor = BatchSpanProcessor(span_exporter)
    provider.add_span_processor(span_processor)

    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
    app.state.otel_tracing_enabled = True
    app.state.otel_tracer_provider = provider


def shutdown_tracing(app: FastAPI) -> None:
    provider = getattr(app.state, "otel_tracer_provider", None)
    if provider:
        provider.shutdown()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    try:
        elastic_enabled = elastic_client.enabled
        vertex_enabled = vertex_client.enabled
        if elastic_enabled:
            await elastic_client.ensure_client()
        if vertex_enabled:
            vertex_client.ensure_init()
        yield
    finally:
        if elastic_client.enabled:
            await elastic_client.close()
        shutdown_tracing(app)
