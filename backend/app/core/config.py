from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    project_name: str = "EverydayElastic API"
    environment: str = "local"
    vertex_project_id: str | None = ""
    vertex_location: str = "us-central1"
    elastic_endpoint: str | None = ""
    elastic_api_key: str | None = None
    elastic_username: str | None = None
    elastic_password: str | None = None
    vertex_model: str = "gemini-1.5-pro"
    google_application_credentials: str | None = None
    default_index_name: str = "knowledge-base"
    request_timeout_seconds: int = 30
    embedding_inference_id: str = "google_vertex_ai_embedding"
    reranker_inference_id: str = ""
    search_result_size: int = 8
    max_context_chunks: int = 4
    jira_webhook_url: str | None = None
    slack_webhook_url: str | None = None
    slack_access_token: str | None = None
    slack_refresh_token: str | None = None
    slack_client_id: str | None = None
    slack_client_secret: str | None = None
    default_slack_channel: str = "#sev-1-war-room"
    locale_index_overrides: dict[str, str] = Field(default_factory=dict)
    enable_tracing: bool = False
    otel_exporter_endpoint: str | None = None
    otel_exporter_headers: str | None = None
    otel_exporter_insecure: bool = False


settings = Settings()
