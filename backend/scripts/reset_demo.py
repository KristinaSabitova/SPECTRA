"""
Reset SPECTRA database completely.

Deletes all rows from every table (users, pipelines, audits, execution runs/events,
sessions, access logs, agents) while preserving the schema and Alembic version.
After running this, the app will show the initial-setup screen.

Usage:
    cd backend
    python scripts/reset_demo.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.models  # noqa: F401 — registers all models with Base.metadata
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.db.database import Base

# Tables to wipe, in deletion order (respects FK constraints)
TABLES = [
    "access_logs",
    "sessions",
    "execution_events",
    "execution_runs",
    "audits",
    "agents",
    "pipelines",
    "users",
]

LABELS = {
    "users":            "Usuarios",
    "sessions":         "Sesiones activas",
    "access_logs":      "Registros de acceso",
    "pipelines":        "Pipelines",
    "audits":           "Auditorías",
    "execution_runs":   "Ejecuciones",
    "execution_events": "Eventos de ejecución",
    "agents":           "Agentes",
}


async def get_counts(db) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in TABLES:
        result = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
        counts[table] = result.scalar_one()
    return counts


def print_summary(counts: dict[str, int]) -> None:
    total = sum(counts.values())
    print()
    print("  Registros que se van a eliminar:")
    print("  " + "─" * 42)
    for table in TABLES:
        n = counts[table]
        label = LABELS.get(table, table)
        marker = "  " if n == 0 else "→ "
        print(f"  {marker}{label:<28} {n:>5} registros")
    print("  " + "─" * 42)
    print(f"  {'TOTAL':<28} {total:>5} registros")
    print()


async def main() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║         SPECTRA — Reset completo de DB           ║")
    print("╚══════════════════════════════════════════════════╝")

    async with Session() as db:
        print("\n  Analizando base de datos…")
        counts = await get_counts(db)

    total = sum(counts.values())
    print_summary(counts)

    if total == 0:
        print("  La base de datos ya está vacía. Nada que hacer.")
        print()
        await engine.dispose()
        return

    print("  ⚠  Esta operación NO se puede deshacer.")
    print("     La app mostrará la pantalla de setup inicial.")
    print()
    answer = input("  Escribe 'si' para confirmar: ").strip().lower()

    if answer != "si":
        print("\n  Operación cancelada.\n")
        await engine.dispose()
        sys.exit(0)

    print()
    print("  Eliminando registros…")
    print()

    async with Session() as db:
        # Disable FK checks for SQLite so we can delete in any order
        await db.execute(text("PRAGMA foreign_keys = OFF"))

        deleted_total = 0
        for table in TABLES:
            n = counts[table]
            if n == 0:
                print(f"  ✓  {LABELS.get(table, table):<28} (vacía, sin cambios)")
                continue
            await db.execute(text(f"DELETE FROM {table}"))
            deleted_total += n
            print(f"  ✗  {LABELS.get(table, table):<28} {n} registros eliminados")

        await db.execute(text("PRAGMA foreign_keys = ON"))
        await db.commit()

    print()
    print("  Recreando esquema de tablas…")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("  ✓  Esquema verificado y actualizado")

    await engine.dispose()

    print()
    print("  " + "═" * 48)
    print(f"  Reset completado — {deleted_total} registros eliminados")
    print("  " + "═" * 48)
    print()
    print("  La base de datos está vacía.")
    print("  Al abrir SPECTRA aparecerá la pantalla de setup inicial.")
    print()


if __name__ == "__main__":
    asyncio.run(main())
