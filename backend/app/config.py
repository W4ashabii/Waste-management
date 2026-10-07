from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite+aiosqlite:///./waste_management.db"
    MODEL_SERVICE_URL: str = "http://localhost:8001"
    MODEL_SERVICE_TIMEOUT: float = 30.0
    SECRET_KEY: str = "dev-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 12 * 60
    # Comma-separated list of origins allowed to call the API from a browser.
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    # Optional regex for extra origins (e.g. preview deployments).
    CORS_ORIGIN_REGEX: str | None = None
    # Seed the demo data from app/seed_data when the database is empty.
    SEED_ON_STARTUP: bool = True
    MAX_IMAGE_BYTES: int = 10 * 1024 * 1024
    SQL_ECHO: bool = False

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
