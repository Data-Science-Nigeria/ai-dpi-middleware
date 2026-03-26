from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # JWT (local tokens)
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

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
    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-4-6"

    # CORS
    cors_origins: list[str] = ["*"]


settings = Settings()  # type: ignore[call-arg]
