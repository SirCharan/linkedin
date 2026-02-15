from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    linkedin_client_id: str
    linkedin_client_secret: str
    linkedin_redirect_uri: str = "http://localhost:8000/auth/callback"
    app_secret_key: str = "change-me"
    linkedin_api_version: str = "202502"
    linkedin_email: str = ""
    linkedin_password: str = ""
    linkedin_li_at: str = ""
    linkedin_jsessionid: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
