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
    # Google Wallet — set these to enable "Add to Google Wallet" button
    GOOGLE_WALLET_ISSUER_ID: str = ""
    GOOGLE_WALLET_SA_KEY_PATH: str = ""  # path to service account JSON key
    # Apple Wallet — set these to enable "Add to Apple Wallet" button
    APPLE_PASS_TYPE_ID: str = ""
    APPLE_PASS_TEAM_ID: str = ""
    APPLE_PASS_CERT_PATH: str = ""  # PEM certificate
    APPLE_PASS_KEY_PATH: str = ""  # PEM private key
    APPLE_PASS_KEY_PASSWORD: str = ""
    APPLE_WWDR_CERT_PATH: str = ""  # Apple WWDR intermediate cert


settings = Settings()
