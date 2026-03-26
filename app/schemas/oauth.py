from pydantic import BaseModel


class OAuth2CallbackParams(BaseModel):
    code: str
    state: str | None = None


class OAuth2ClientCredentialsRequest(BaseModel):
    client_id: str
    client_secret: str
    scope: str | None = None


class OAuth2TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int | None = None
    id_token: str | None = None
    scope: str | None = None
