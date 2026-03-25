from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    app_name: str = "AI DPI Middleware"
    app_version: str = "0.1.0"
    debug: bool = False

    # OAuth2
    oauth_issuer: str  # e.g. https://accounts.google.com
    oauth_client_id: str
    oauth_client_secret: str
    oauth_audience: str = ""  # expected audience claim in JWT; leave empty to skip check
    jwks_uri: str  # e.g. https://accounts.google.com/.well-known/openid-configuration/jwks

    # Anthropic
    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-4-6"

    # CORS
    cors_origins: list[str] = ["*"]


settings = Settings()  # type: ignore[call-arg]