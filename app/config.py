from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    linkedin_client_id: str
    linkedin_client_secret: str
    linkedin_redirect_uri: str = "http://localhost:8000/auth/callback"
    anthropic_api_key: str
    app_secret_key: str = "change-me"
    linkedin_api_version: str = "202401"
    claude_model: str = "claude-sonnet-4-5-20250929"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
