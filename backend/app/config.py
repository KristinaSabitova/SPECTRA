from datetime import timedelta

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "development"
    app_secret_key: str = "dev-secret-key-change-in-production"
    app_debug: bool = True

    # Set DATABASE_URL to use PostgreSQL in production:
    #   postgresql+asyncpg://user:pass@host:5432/dbname
    # Defaults to SQLite for local development.
    database_url: str = "sqlite+aiosqlite:///./spectra.db"

    cors_origins: list[str] = ["http://localhost:3000"]

    # JWT
    jwt_secret_key: str = "dev-jwt-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    jwt_2fa_temp_expire_minutes: int = 5

    # TOTP
    totp_issuer: str = "SPECTRA"

    @property
    def access_token_expire(self) -> timedelta:
        return timedelta(minutes=self.jwt_access_token_expire_minutes)

    @property
    def refresh_token_expire(self) -> timedelta:
        return timedelta(days=self.jwt_refresh_token_expire_days)

    class Config:
        env_file = ".env"


settings = Settings()
