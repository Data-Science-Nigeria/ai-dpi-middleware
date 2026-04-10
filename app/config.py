from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config_yaml import get_yaml_config

_yaml_jwt = get_yaml_config().jwt


class ClientConfig(BaseModel):
    secret: str
    roles: list[str] = []


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    app_name: str = "AI DPI Middleware"
    app_version: str = "0.1.0"
    debug: bool = False

    # Client registry: maps client_id -> {secret, roles}
    # JSON env var, e.g.:
    # CLIENTS={"app1":{"secret":"s3cr3t","roles":["user"]},"admin":{"secret":"s3cr3t","roles":["admin","user"]}}
    clients: dict[str, ClientConfig] = {}

    # JWT (local tokens) — defaults come from default_config.yaml, overridable via .env
    jwt_secret: str
    jwt_algorithm: str = _yaml_jwt.jwt_algorithm
    jwt_expire_minutes: int = _yaml_jwt.jwt_expire_minutes

    # OIDC / OAuth2 (optional — set to enable external provider tokens & flows)
    oidc_issuer: str | None = None
    oidc_jwks_uri: str | None = None
    oidc_audience: str | None = None         # validate `aud` claim if set

    # OAuth2 Authorization Code + Client Credentials flows
    oauth2_client_id: str | None = None
    oauth2_client_secret: str | None = None
    oauth2_authorization_endpoint: str | None = None
    oauth2_token_endpoint: str | None = None
    oauth2_redirect_uri: str | None = None
    oauth2_scopes: list[str] = ["openid", "profile", "email"]

    # Anthropic
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"

    # Groq
    groq_api_key: str | None = None
    groq_model: str = "groq-1.5-pro"

    # OpenAI
    openai_api_key: str | None = None

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    oauth2_state_ttl_seconds: int = 300  # how long a login state token is valid

    # CORS
    cors_origins: list[str] = ["*"]


settings = Settings()  # type: ignore[call-arg]
