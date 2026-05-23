# SPECTRA

**Herramienta profesional de red team para auditoría de pipelines de agentes IA.**

SPECTRA permite a equipos de seguridad identificar, analizar y reportar vulnerabilidades en arquitecturas de agentes IA: prompt injection, escalada de privilegios, fugas de contexto, y comportamientos no autorizados en cadenas de herramientas.

---

## Stack tecnológico

| Capa       | Tecnología                          |
|------------|-------------------------------------|
| Backend    | Python 3.12 · FastAPI · SQLAlchemy  |
| Frontend   | React 18 · TypeScript · Vite        |
| Base datos | PostgreSQL                          |
| Infra      | Docker · Docker Compose · Nginx     |

---

## Estructura del proyecto

```
SPECTRA/
├── backend/        # API FastAPI, lógica de auditoría y modelos
├── frontend/       # Interfaz React/TypeScript
├── config/         # Nginx, scripts de inicialización
├── docker-compose.yml
└── .env.example
```

---

## Inicio rápido

### Prerrequisitos

- Docker y Docker Compose instalados
- Python 3.12+ (para desarrollo local del backend)
- Node.js 20+ (para desarrollo local del frontend)

### Con Docker (recomendado)

```bash
cp .env.example .env
# Editar .env con tus valores
docker-compose up --build
```

La aplicación estará disponible en `http://localhost`.

### Desarrollo local

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## Módulos principales

- **Agent Scanner** — Fingerprinting y enumeración de agentes expuestos
- **Pipeline Auditor** — Análisis de flujos multi-agente en busca de vectores de ataque
- **Report Generator** — Generación de informes en formato estructurado

---

## Licencia

Uso interno. Distribución restringida.
