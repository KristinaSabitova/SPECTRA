#!/usr/bin/env python3
"""
Verify cross-tenant isolation, demo pipeline seed, and audit launch.

Registers two fresh trial users per run (unique emails via run-ID suffix),
then asserts isolation, seed correctness and audit flow against a local instance.

Usage:
    cd backend
    python scripts/verify_isolation.py

Env overrides (all optional):
    BASE_URL      default http://localhost:8000/api/v1
    INVITE_CODE   default TalentDay2026
    TEST_PASSWORD default Spectra!Verify2026
"""
from __future__ import annotations

import os
import sys
import uuid

import httpx

# ── Config ────────────────────────────────────────────────────────────────────

BASE_URL    = os.getenv("BASE_URL",      "http://localhost:8000/api/v1")
INVITE_CODE = os.getenv("INVITE_CODE",   "TalentDay2026")
PASSWORD    = os.getenv("TEST_PASSWORD", "Spectra!Verify2026")

DEMO_LAB_NAME      = "Demo — Lab Agent (vulnerable)"
DEMO_RAILWAY_NAME  = "Demo — Agente resistente (Railway)"

# ── Result tracking ───────────────────────────────────────────────────────────

_results: list[tuple[str, str]] = []


def check(label: str, condition: bool, detail: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    _results.append((status, label))
    suffix = f"  ({detail})" if detail else ""
    print(f"  [{status}] {label}{suffix}")
    return condition


def summary() -> None:
    passed = sum(1 for s, _ in _results if s == "PASS")
    failed = sum(1 for s, _ in _results if s == "FAIL")
    print("\n" + "═" * 56)
    print("  RESUMEN")
    print("═" * 56)
    for status, label in _results:
        print(f"  [{status}] {label}")
    print(f"\n  {passed} PASS  |  {failed} FAIL")
    print("═" * 56)

# ── HTTP helpers ──────────────────────────────────────────────────────────────

def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register(client: httpx.Client, email: str, username: str) -> httpx.Response:
    return client.post("/auth/register", json={
        "email":       email,
        "username":    username,
        "password":    PASSWORD,
        "invite_code": INVITE_CODE,
    })


def login(client: httpx.Client, email: str) -> tuple[str, str]:
    """Returns (access_token, role)."""
    r = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    r.raise_for_status()
    data = r.json()
    if data.get("requires_2fa"):
        raise RuntimeError(f"Unexpected 2FA challenge for {email}")
    return data["tokens"]["access_token"], data["user"]["role"]


def get_pipelines(client: httpx.Client, token: str) -> list[dict]:
    r = client.get("/pipelines/", headers=auth_header(token))
    r.raise_for_status()
    return r.json()

# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    run_id = uuid.uuid4().hex[:8]
    email_a    = f"empresa_a_{run_id}@test.local"
    email_b    = f"empresa_b_{run_id}@test.local"
    username_a = f"empresa_a_{run_id}"
    username_b = f"empresa_b_{run_id}"

    print(f"\nSPECTRA — verify_isolation  (run {run_id})")
    print(f"Target: {BASE_URL}\n")

    with httpx.Client(base_url=BASE_URL, timeout=30) as client:

        # ── 1. Registro ───────────────────────────────────────────────────────
        print("── 1. Registro ──────────────────────────────────────────")
        ra = register(client, email_a, username_a)
        check("Usuario A registrado (201)", ra.status_code == 201,
              f"HTTP {ra.status_code}" if ra.status_code != 201 else "")
        rb = register(client, email_b, username_b)
        check("Usuario B registrado (201)", rb.status_code == 201,
              f"HTTP {rb.status_code}" if rb.status_code != 201 else "")

        if ra.status_code != 201 or rb.status_code != 201:
            print("\n  Registro fallido — abortando el resto de comprobaciones.")
            summary()
            sys.exit(1)

        # ── 2. Login ──────────────────────────────────────────────────────────
        print("\n── 2. Login y rol ───────────────────────────────────────")
        token_a, role_a = login(client, email_a)
        token_b, role_b = login(client, email_b)
        check("Usuario A: rol = trial", role_a == "trial", f"rol actual: {role_a}")
        check("Usuario B: rol = trial", role_b == "trial", f"rol actual: {role_b}")

        # ── 3. Seed de pipelines demo ─────────────────────────────────────────
        print("\n── 3. Seed de pipelines demo ────────────────────────────")
        pipes_a = get_pipelines(client, token_a)
        pipes_b = get_pipelines(client, token_b)
        names_a = {p["name"] for p in pipes_a}
        names_b = {p["name"] for p in pipes_b}

        check("A: pipeline Lab Agent sembrado",
              any(DEMO_LAB_NAME in n for n in names_a), str(names_a))
        check("B: pipeline Lab Agent sembrado",
              any(DEMO_LAB_NAME in n for n in names_b), str(names_b))

        # Si DEMO_RAILWAY_URL no está configurado en el servidor, el pipeline Railway
        # no se siembra (comportamiento correcto — lo verificamos).
        railway_a = [p for p in pipes_a if DEMO_RAILWAY_NAME in p["name"]]
        if railway_a:
            check("A: pipeline Railway sembrado con endpoint_url no vacío",
                  bool(railway_a[0]["endpoint_url"]),
                  str(railway_a[0]["endpoint_url"]))
        else:
            print("  [INFO] Pipeline Railway omitido en A (DEMO_RAILWAY_URL no configurada) — correcto")

        null_pipes_a = [p["name"] for p in pipes_a if not p.get("endpoint_url")]
        null_pipes_b = [p["name"] for p in pipes_b if not p.get("endpoint_url")]
        check("A: ningún pipeline con endpoint_url vacío", not null_pipes_a,
              f"pipelines con URL vacía: {null_pipes_a}" if null_pipes_a else "")
        check("B: ningún pipeline con endpoint_url vacío", not null_pipes_b,
              f"pipelines con URL vacía: {null_pipes_b}" if null_pipes_b else "")

        # ── 4. Aislamiento cross-tenant ───────────────────────────────────────
        print("\n── 4. Aislamiento cross-tenant ──────────────────────────")
        ids_a = {p["id"] for p in pipes_a}
        ids_b = {p["id"] for p in pipes_b}
        overlap = ids_a & ids_b

        check("A no ve ningún pipeline de B", not overlap,
              f"IDs en común: {overlap}" if overlap else "")
        check("B no ve ningún pipeline de A", not overlap,
              f"IDs en común: {overlap}" if overlap else "")
        check("A ve al menos 1 pipeline propio", len(pipes_a) >= 1,
              f"{len(pipes_a)} pipelines")
        check("B ve al menos 1 pipeline propio", len(pipes_b) >= 1,
              f"{len(pipes_b)} pipelines")

        # Verificación explícita de owner: ningún pipeline de A aparece en B y viceversa
        ids_only_a = ids_a - ids_b
        ids_only_b = ids_b - ids_a
        check("Todos los pipelines de A son exclusivos de A",
              ids_only_a == ids_a and len(ids_a) > 0)
        check("Todos los pipelines de B son exclusivos de B",
              ids_only_b == ids_b and len(ids_b) > 0)

        # ── 5. Flujo de auditoría ─────────────────────────────────────────────
        print("\n── 5. Flujo de auditoría (POST /audits/) ────────────────")
        lab_pipe = next((p for p in pipes_a if DEMO_LAB_NAME in p["name"]), None)
        if lab_pipe:
            r_audit = client.post(
                "/audits/",
                headers=auth_header(token_a),
                json={"pipeline_id": lab_pipe["id"], "name": f"verify-run-{run_id}"},
            )
            check("POST /audits/ con rol trial → 2xx",
                  r_audit.status_code in (200, 201, 202),
                  f"HTTP {r_audit.status_code}")
            if r_audit.status_code in (200, 201, 202):
                audit_data = r_audit.json()
                check("Respuesta de auditoría contiene id y status",
                      "id" in audit_data and "status" in audit_data,
                      str(audit_data))
        else:
            check("POST /audits/ con rol trial → 2xx", False,
                  "pipeline Lab Agent no encontrado en A — revisa el seed")

    summary()
    failed = sum(1 for s, _ in _results if s == "FAIL")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
