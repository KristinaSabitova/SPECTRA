#!/usr/bin/env bash
# Genera certificado autofirmado para desarrollo local.
# En producción usar Let's Encrypt / cert real.
set -euo pipefail

CERTS_DIR="$(cd "$(dirname "$0")/../certs" && pwd)"
mkdir -p "$CERTS_DIR"

openssl req -x509 -nodes -days 365 \
  -newkey rsa:4096 \
  -keyout "$CERTS_DIR/spectra.key" \
  -out    "$CERTS_DIR/spectra.crt" \
  -subj "/C=XX/ST=Dev/L=Local/O=SPECTRA/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

chmod 600 "$CERTS_DIR/spectra.key"

echo "Certificado generado en $CERTS_DIR"
echo "  → spectra.crt (cert)"
echo "  → spectra.key (clave privada)"
echo ""
echo "Para confiar en él localmente:"
echo "  macOS:   sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain $CERTS_DIR/spectra.crt"
echo "  Linux:   sudo cp $CERTS_DIR/spectra.crt /usr/local/share/ca-certificates/ && sudo update-ca-certificates"
