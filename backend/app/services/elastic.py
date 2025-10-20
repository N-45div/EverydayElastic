from __future__ import annotations

import logging
from typing import Any

from elasticsearch import AsyncElasticsearch, BadRequestError

from ..core.config import settings


logger = logging.getLogger(__name__)


class ElasticClient:
    def __init__(
        self,
        endpoint: str,
        api_key: str | None,
        username: str | None,
        password: str | None,
        index_name: str,
        request_timeout: int,
        embedding_inference_id: str,
        reranker_inference_id: str,
        locale_index_overrides: dict[str, str] | None = None,
    ) -> None:
        self._endpoint = endpoint
        self._api_key = api_key
        self._username = username
        self._password = password
        self._index_name = index_name
        self._request_timeout = request_timeout
        self._embedding_inference_id = embedding_inference_id
        self._reranker_inference_id = reranker_inference_id
        self._locale_index_overrides = {
            (key or "").lower(): value
            for key, value in (locale_index_overrides or {}).items()
            if value
        }
        self._client: AsyncElasticsearch | None = None

    @property
    def enabled(self) -> bool:
        return bool(self._endpoint)

    async def ensure_client(self) -> AsyncElasticsearch:
        if not self.enabled:
            raise RuntimeError("Elastic endpoint is not configured")
        if self._client is None:
            client_kwargs: dict[str, Any] = {
                "hosts": [self._endpoint],
                "request_timeout": self._request_timeout,
            }
            if self._api_key:
                client_kwargs["api_key"] = self._api_key
            elif self._username and self._password:
                client_kwargs["basic_auth"] = (self._username, self._password)
            self._client = AsyncElasticsearch(**client_kwargs)
        return self._client

    async def health(self) -> dict[str, Any]:
        if not self.enabled:
            return {"status": "disabled"}
        client = await self.ensure_client()
        return await client.cluster.health()

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None

    @property
    def index_name(self) -> str:
        return self._index_name

    @property
    def embedding_inference_id(self) -> str:
        return self._embedding_inference_id

    @property
    def reranker_inference_id(self) -> str:
        return self._reranker_inference_id

    def resolve_index(self, locale: str | None = None) -> str:
        if not locale:
            return self._index_name
        locale_key = locale.lower()
        if locale_key in self._locale_index_overrides:
            return self._locale_index_overrides[locale_key]
        base_lang = locale_key.split("-")[0]
        return self._locale_index_overrides.get(base_lang, self._index_name)

    async def semantic_search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        *,
        locale: str | None = None,
        size: int | None = None,
    ) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        client = await self.ensure_client()
        search_size = size or settings.search_result_size
        target_index = self.resolve_index(locale)

        filter_clauses: list[dict[str, Any]] = []
        if filters:
            for field, value in filters.items():
                if value is None:
                    continue
                if isinstance(value, (list, tuple, set)):
                    filter_clauses.append({"terms": {field: list(value)}})
                else:
                    filter_clauses.append({"term": {field: value}})

        def build_semantic_query() -> dict[str, Any]:
            semantic_clause: dict[str, Any] = {
                "semantic": {
                    "field": "content",
                    "query": query,
                }
            }
            if not filter_clauses:
                return {"size": search_size, "query": semantic_clause}
            return {
                "size": search_size,
                "query": {"bool": {"filter": filter_clauses, "must": [semantic_clause]}},
            }

        def build_keyword_query() -> dict[str, Any]:
            match_clause: dict[str, Any] = {
                "match": {"content": {"query": query, "operator": "and"}}
            }
            if not filter_clauses:
                return {"size": search_size, "query": match_clause}
            return {
                "size": search_size,
                "query": {"bool": {"filter": filter_clauses, "must": [match_clause]}},
            }

        use_semantic = bool(self._embedding_inference_id)
        body = build_semantic_query() if use_semantic else build_keyword_query()
        try:
            result = await client.search(index=target_index, body=body)
        except BadRequestError as exc:
            message = str(exc)
            if "unknown field [inference_id]" in message.lower():
                logger.warning("Semantic search unsupported. Falling back to BM25: %s", exc)
                result = await client.search(index=target_index, body=build_keyword_query())
            else:
                logger.warning("Elastic search failed with bad request: %s", exc)
                return []
        except Exception as exc:  # noqa: BLE001
            logger.warning("Elastic search failed: %s", exc)
            return []
        hits = result.get("hits", {}).get("hits", [])
        return hits

    async def rerank(self, query: str, hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if (
            not self.enabled
            or not hits
            or not self._reranker_inference_id
            or not self._reranker_inference_id.strip()
        ):
            return hits
        texts: list[str] = []
        for hit in hits:
            source = hit.get("_source", {})
            content = source.get("content") or source.get("text") or ""
            texts.append(content)
        if not texts:
            return hits
        client = await self.ensure_client()
        payload = {"query": query, "input": texts}
        try:
            # Use the inference namespace which handles auth properly
            response = await client.inference.inference(
                inference_id=self._reranker_inference_id,
                body=payload,
            )
            # Extract body from response
            response_body = response.body if hasattr(response, 'body') else response
        except Exception as exc:  # noqa: BLE001
            logger.warning("Elastic rerank request failed: %s", exc)
            return hits
        rankings = response_body.get("rerank", [])
        ordered: list[dict[str, Any]] = []
        seen = set()
        for item in rankings:
            idx = item.get("index")
            if idx is None or idx in seen or idx >= len(hits):
                continue
            hit = hits[idx]
            hit.setdefault("_rerank", {})
            hit["_rerank"]["relevance_score"] = item.get("relevance_score")
            ordered.append(hit)
            seen.add(idx)
        for idx, hit in enumerate(hits):
            if idx not in seen:
                ordered.append(hit)
        return ordered

    @classmethod
    def from_settings(cls) -> "ElasticClient":
        return cls(
            endpoint=settings.elastic_endpoint or "",
            api_key=settings.elastic_api_key,
            username=settings.elastic_username,
            password=settings.elastic_password,
            index_name=settings.default_index_name,
            request_timeout=settings.request_timeout_seconds,
            embedding_inference_id=settings.embedding_inference_id,
            reranker_inference_id=settings.reranker_inference_id,
            locale_index_overrides=settings.locale_index_overrides,
        )
