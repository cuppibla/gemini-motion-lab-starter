from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    GOOGLE_CLOUD_PROJECT: str = "your-project"
    GOOGLE_CLOUD_LOCATION: str = "us-central1"
    GCS_BUCKET: str = "gemini-motion-lab"
    GCS_SIGNING_SA: str = ""
    GOOGLE_GENAI_USE_VERTEXAI: bool = True
    MOCK_AI: bool = False
    PUBLIC_BASE_URL: str = "http://localhost:8000"


settings = Settings()
