import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

from app.models.user import UserRole

_PASSWORD_RE = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]).{12,}$"
)
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,50}$")
_TOTP_CODE_RE = re.compile(r"^\d{6}$")
_BACKUP_CODE_RE = re.compile(r"^[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}$")


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    role: UserRole = UserRole.junior

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not _USERNAME_RE.match(v):
            raise ValueError("username: 3-50 chars, only letters, digits and underscores")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not _PASSWORD_RE.match(v):
            raise ValueError(
                "password must be ≥12 chars with uppercase, lowercase, digit and special char"
            )
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class TOTPLoginRequest(BaseModel):
    temp_token: str
    code: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not _TOTP_CODE_RE.match(v) and not _BACKUP_CODE_RE.match(v):
            raise ValueError("code must be 6 digits or a backup code (XXXX-XXXX)")
        return v


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    role: UserRole
    is_active: bool
    is_temporary_password: bool
    totp_enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    requires_2fa: bool = False
    must_change_password: bool = False
    temp_token: str | None = None
    tokens: TokenResponse | None = None
    user: "UserResponse | None" = None


class SessionResponse(BaseModel):
    id: str
    ip_address: str
    user_agent: str | None
    created_at: datetime
    expires_at: datetime
    is_current: bool = False

    model_config = {"from_attributes": True}


class TOTPSetupResponse(BaseModel):
    secret: str
    qr_uri: str
    backup_codes: list[str]


class TOTPEnableRequest(BaseModel):
    code: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not _TOTP_CODE_RE.match(v):
            raise ValueError("code must be 6 digits")
        return v


class TOTPDisableRequest(BaseModel):
    code: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not _TOTP_CODE_RE.match(v) and not _BACKUP_CODE_RE.match(v):
            raise ValueError("code must be 6 digits or a backup code")
        return v


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if not _PASSWORD_RE.match(v):
            raise ValueError(
                "password must be ≥12 chars with uppercase, lowercase, digit and special char"
            )
        return v


class CreateUserRequest(BaseModel):
    email: EmailStr
    username: str
    role: UserRole = UserRole.junior

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not _USERNAME_RE.match(v):
            raise ValueError("username: 3-50 chars, only letters, digits and underscores")
        return v


class CreateUserResponse(BaseModel):
    user: "UserResponse"
    temp_password: str


LoginResponse.model_rebuild()
CreateUserResponse.model_rebuild()
