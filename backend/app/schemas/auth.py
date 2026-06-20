import re
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole

_PASSWORD_RE = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]).{12,}$"
)
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,50}$")
_TOTP_CODE_RE = re.compile(r"^\d{6}$")
_BACKUP_CODE_RE = re.compile(r"^[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}$")


class RegisterRequest(BaseModel):
    email: Annotated[EmailStr, Field(max_length=255)]
    username: Annotated[str, Field(min_length=3, max_length=50)]
    password: Annotated[str, Field(min_length=12, max_length=128)]
    invite_code: Annotated[str, Field(max_length=128)] = ""
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
    email: Annotated[str, Field(max_length=255)]
    password: Annotated[str, Field(max_length=128)]


class TOTPLoginRequest(BaseModel):
    temp_token: Annotated[str, Field(max_length=512)]
    code: Annotated[str, Field(max_length=10)]

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not _TOTP_CODE_RE.match(v) and not _BACKUP_CODE_RE.match(v):
            raise ValueError("code must be 6 digits or a backup code (XXXX-XXXX)")
        return v


class TokenResponse(BaseModel):
    access_token: str
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
    # password_hash is intentionally excluded from all response schemas

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    requires_2fa: bool = False
    must_change_password: bool = False
    must_setup_totp: bool = False
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
    code: Annotated[str, Field(max_length=10)]

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not _TOTP_CODE_RE.match(v):
            raise ValueError("code must be 6 digits")
        return v


class TOTPDisableRequest(BaseModel):
    code: Annotated[str, Field(max_length=10)]

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not _TOTP_CODE_RE.match(v) and not _BACKUP_CODE_RE.match(v):
            raise ValueError("code must be 6 digits or a backup code")
        return v


class ChangePasswordRequest(BaseModel):
    current_password: Annotated[str, Field(max_length=128)]
    new_password: Annotated[str, Field(min_length=12, max_length=128)]

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if not _PASSWORD_RE.match(v):
            raise ValueError(
                "password must be ≥12 chars with uppercase, lowercase, digit and special char"
            )
        return v


class CreateUserRequest(BaseModel):
    email: Annotated[EmailStr, Field(max_length=255)]
    username: Annotated[str, Field(min_length=3, max_length=50)]
    invite_code: Annotated[str, Field(max_length=128)] = ""
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


class AuditLogEntry(BaseModel):
    id: str
    action: str
    success: bool
    ip_address: str
    created_at: datetime

    model_config = {"from_attributes": True}


LoginResponse.model_rebuild()
CreateUserResponse.model_rebuild()
