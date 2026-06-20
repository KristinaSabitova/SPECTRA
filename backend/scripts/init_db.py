"""
Initialize the SPECTRA database and seed a default admin user.

Usage:
    python scripts/init_db.py
    python scripts/init_db.py --email admin@example.com --password secret123
    python scripts/init_db.py --reset   # drops and recreates all tables
"""
from __future__ import annotations

import argparse
import asyncio
import secrets
import sys
from pathlib import Path

# Allow running from repo root or scripts/ directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import settings


async def main(email: str, username: str, password: str, reset: bool) -> None:
    # Import models so Base.metadata knows about all tables
    from app.db.database import Base
    import app.models.user          # noqa: F401
    import app.models.access_log    # noqa: F401
    import app.models.execution     # noqa: F401
    import app.models.pipeline      # noqa: F401

    from app.models.user import User, UserRole

    engine = create_async_engine(settings.database_url, echo=False)

    async with engine.begin() as conn:
        if reset:
            print("Dropping all tables...")
            await conn.run_sync(Base.metadata.drop_all)

        print(f"Creating tables on: {settings.database_url}")
        await conn.run_sync(Base.metadata.create_all)

    # Hash password with argon2
    try:
        from argon2 import PasswordHasher
        ph = PasswordHasher()
        password_hash = ph.hash(password)
    except ImportError:
        import hashlib, secrets
        salt = secrets.token_hex(16)
        password_hash = f"sha256${salt}${hashlib.sha256((salt + password).encode()).hexdigest()}"
        print("WARNING: argon2-cffi not installed — using SHA-256 fallback (not safe for production)")

    import uuid
    from datetime import datetime, timezone

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as db:
        from sqlalchemy import select
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            print(f"User '{email}' already exists — skipping creation.")
        else:
            admin = User(
                id=str(uuid.uuid4()),
                email=email,
                username=username,
                password_hash=password_hash,
                role=UserRole.admin,
                is_active=True,
                totp_enabled=False,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(admin)
            await db.commit()
            print(f"Created admin user: {email} / {username}")

    await engine.dispose()
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize SPECTRA database")
    parser.add_argument("--email",    default="admin@example.com")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default=None)
    parser.add_argument("--reset",    action="store_true",
                        help="Drop and recreate all tables (destructive!)")
    args = parser.parse_args()

    if args.password is None:
        args.password = secrets.token_urlsafe(16)
        print(f"Generated admin password: {args.password}")

    if args.reset:
        confirm = input("This will DELETE all data. Type 'yes' to continue: ")
        if confirm.strip().lower() != "yes":
            print("Aborted.")
            sys.exit(0)

    asyncio.run(main(
        email=args.email,
        username=args.username,
        password=args.password,
        reset=args.reset,
    ))
