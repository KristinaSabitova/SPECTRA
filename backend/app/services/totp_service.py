import hashlib
import secrets
from typing import TYPE_CHECKING

import pyotp

from app.config import settings
from app.core.security import decrypt_secret, encrypt_secret

if TYPE_CHECKING:
    from app.models.user import User


class TOTPService:
    BACKUP_CODE_COUNT = 8

    def generate_setup(self, email: str) -> dict:
        secret = pyotp.random_base32()
        uri = pyotp.TOTP(secret).provisioning_uri(
            name=email, issuer_name=settings.totp_issuer
        )
        backup_codes = self._generate_backup_codes()
        return {
            "secret": secret,
            "qr_uri": uri,
            "backup_codes": backup_codes,
        }

    def verify(self, user: "User", code: str) -> tuple[bool, bool]:
        """Returns (valid, used_backup). On backup code use the caller must remove it."""
        if not user.totp_secret_enc:
            return False, False
        secret = decrypt_secret(user.totp_secret_enc)

        # Código TOTP normal (ventana ±30 s)
        if pyotp.TOTP(secret).verify(code, valid_window=1):
            return True, False

        # Código de respaldo
        if self._check_backup_code(user, code):
            return True, True

        return False, False

    def _generate_backup_codes(self) -> list[str]:
        return [
            f"{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}"
            for _ in range(self.BACKUP_CODE_COUNT)
        ]

    @staticmethod
    def hash_code(code: str) -> str:
        return hashlib.sha256(code.strip().upper().encode()).hexdigest()

    def hash_backup_codes(self, codes: list[str]) -> list[str]:
        return [self.hash_code(c) for c in codes]

    def _check_backup_code(self, user: "User", code: str) -> bool:
        if not user.backup_codes_hash:
            return False
        return self.hash_code(code) in user.backup_codes_hash

    def consume_backup_code(self, user: "User", code: str) -> None:
        if user.backup_codes_hash:
            h = self.hash_code(code)
            user.backup_codes_hash = [x for x in user.backup_codes_hash if x != h]

    @staticmethod
    def apply_setup(user: "User", secret: str, codes_hash: list[str]) -> None:
        user.totp_secret_enc = encrypt_secret(secret)
        user.totp_enabled = True
        user.backup_codes_hash = codes_hash

    @staticmethod
    def disable(user: "User") -> None:
        user.totp_secret_enc = None
        user.totp_enabled = False
        user.backup_codes_hash = None
