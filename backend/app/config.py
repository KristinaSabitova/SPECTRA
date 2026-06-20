import sys
from datetime import timedelta

from pydantic_settings import BaseSettings

_DEFAULT_SECRET = "dev-secret-key-change-in-production"
_DEFAULT_JWT = "dev-jwt-secret-change-in-production"
# base64url(b"dev-totp-key-must-change-in-prod") — valid Fernet key, dev only
_DEFAULT_TOTP_KEY = "ZGV2LXRvdHAta2V5LW11c3QtY2hhbmdlLWluLXByb2Q="


class Settings(BaseSettings):
    app_env: str = "development"
    app_secret_key: str = _DEFAULT_SECRET
    app_debug: bool = False

    # Set DATABASE_URL to use PostgreSQL in production:
    #   postgresql+asyncpg://user:pass@host:5432/dbname
    # Defaults to SQLite for local development.
    database_url: str = "sqlite+aiosqlite:///./spectra.db"

    # Comma-separated list of allowed CORS origins, or JSON array string.
    # In production, set ALLOWED_ORIGINS to your frontend domain(s).
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"

    # JWT
    jwt_secret_key: str = _DEFAULT_JWT
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    jwt_2fa_temp_expire_minutes: int = 5

    # TOTP
    totp_issuer: str = "SPECTRA"
    # Fernet key for encrypting TOTP secrets at rest.
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    totp_encryption_key: str = _DEFAULT_TOTP_KEY

    # Usage limits (0 = unlimited)
    max_runs_per_day: int = 0
    max_targets: int = 0
    max_run_timeout_seconds: int = 120

    # Data retention
    data_retention_days: int = 90

    # Invite codes — CODE:ROLE pairs, comma-separated.
    # Each code grants the role on the right when used at registration.
    # Example: INVITE_CODES=TalentDay2026:trial,BoardingPass:senior
    # Empty = open registration (role defaults to junior).
    # NOTE: admin and senior roles are blocked by auth_service even via invite;
    #       only junior/trial can be granted this way.
    invite_codes: str = ""

    @property
    def invite_code_map(self) -> dict[str, str]:
        raw = self.invite_codes.strip()
        if not raw:
            return {}
        result: dict[str, str] = {}
        for entry in raw.split(","):
            entry = entry.strip()
            if ":" not in entry:
                continue
            code, role = entry.split(":", 1)
            result[code.strip()] = role.strip()
        return result

    # Demo pipelines seeded on every new registration (set in .env)
    # DEMO_RAILWAY_URL must point to your Railway-hosted agent invoke endpoint
    demo_railway_url: str = ""
    demo_lab_url: str = "https://spectra.ksabitova.dev/lab-agent/invoke"

    # Optional Anthropic API key for SEMANTIC_PARAPHRASE mutation
    anthropic_api_key: str = ""

    @property
    def cors_origins(self) -> list[str]:
        raw = self.allowed_origins.strip()
        if raw.startswith("["):
            import json
            return json.loads(raw)
        return [o.strip() for o in raw.split(",") if o.strip()]

    @property
    def access_token_expire(self) -> timedelta:
        return timedelta(minutes=self.jwt_access_token_expire_minutes)

    @property
    def refresh_token_expire(self) -> timedelta:
        return timedelta(days=self.jwt_refresh_token_expire_days)

    model_config = {"env_file": ".env"}


settings = Settings()


def validate_secrets() -> None:
    """
    Refuse to start with insecure defaults in production.
    Called from the FastAPI lifespan so the error is visible at startup.
    """
    env = settings.app_env.lower()
    if env == "production":
        errors: list[str] = []
        if settings.app_debug:
            errors.append(
                "APP_DEBUG is True in production. Set APP_DEBUG=false in your .env file."
            )
        if settings.app_secret_key == _DEFAULT_SECRET or len(settings.app_secret_key) < 32:
            errors.append(
                "APP_SECRET_KEY is the default value or shorter than 32 characters. "
                "Set a strong random secret in your .env file."
            )
        if settings.jwt_secret_key == _DEFAULT_JWT or len(settings.jwt_secret_key) < 32:
            errors.append(
                "JWT_SECRET_KEY is the default value or shorter than 32 characters. "
                "Set a strong random secret in your .env file."
            )
        if settings.totp_encryption_key == _DEFAULT_TOTP_KEY:
            errors.append(
                "TOTP_ENCRYPTION_KEY is the default dev value. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        if errors:
            for msg in errors:
                print(f"[SPECTRA STARTUP ERROR] {msg}", file=sys.stderr)
            sys.exit(1)
    else:
        # Development: warn but don't exit
        if settings.app_secret_key == _DEFAULT_SECRET:
            print(
                "[SPECTRA WARNING] APP_SECRET_KEY is the default development value. "
                "Change it before deploying to production.",
                file=sys.stderr,
            )
        if settings.jwt_secret_key == _DEFAULT_JWT:
            print(
                "[SPECTRA WARNING] JWT_SECRET_KEY is the default development value. "
                "Change it before deploying to production.",
                file=sys.stderr,
            )
