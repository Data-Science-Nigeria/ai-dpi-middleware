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

    # JWT
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Anthropic
    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-4-6"

    # CORS
    cors_origins: list[str] = ["*"]


settings = Settings()  # type: ignore[call-arg]
