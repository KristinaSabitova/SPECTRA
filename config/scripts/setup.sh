#!/usr/bin/env bash
set -euo pipefail

echo "==> SPECTRA setup"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "    .env creado desde .env.example — edítalo antes de continuar"
fi

echo "==> Levantando servicios..."
docker-compose up --build -d

echo "==> Listo. App disponible en http://localhost"
