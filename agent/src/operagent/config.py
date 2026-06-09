from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """환경변수 기반 설정. 시크릿은 .env(gitignore)에서만 — 코드에 평문 금지."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Anthropic — 비어 있으면 LLM 종합을 건너뛰고 수집한 사실만 게시(graceful)
    anthropic_api_key: str = ""
    operagent_model: str = "claude-opus-4-8"

    # Slack
    slack_bot_token: str = ""
    slack_channel_id: str = ""

    # 관측 스택
    prometheus_url: str = "http://prometheus:9090"
    loki_url: str = "http://loki:3100"

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def slack_enabled(self) -> bool:
        return bool(self.slack_bot_token and self.slack_channel_id)


settings = Settings()
