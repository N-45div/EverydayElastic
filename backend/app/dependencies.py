from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from .services.elastic import ElasticClient
from .services.vertex import VertexAIClient


elastic_client = ElasticClient.from_settings()
vertex_client = VertexAIClient.from_settings()


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
