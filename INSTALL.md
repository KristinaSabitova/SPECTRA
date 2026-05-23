# SPECTRA — Guía de instalación

Instrucciones paso a paso para arrancar SPECTRA desde cero tras clonar el repositorio.

---

## Requisitos previos

| Herramienta | Versión mínima | Comprobación |
|-------------|---------------|--------------|
| Python      | 3.11          | `python3 --version` |
| Node.js     | 18            | `node --version` |
| npm         | 9             | `npm --version` |
| Git         | cualquiera    | `git --version` |

---

## 1. Clonar el repositorio

```bash
git clone <URL-del-repositorio> SPECTRA
cd SPECTRA
```

---

## 2. Configurar el backend

### 2.1 Crear el entorno virtual

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Linux / macOS
# venv\Scripts\activate         # Windows
```

### 2.2 Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2.3 Crear el archivo de variables de entorno

```bash
cp .env.example .env
```

Edita `backend/.env` y ajusta al menos estos valores:

```env
APP_SECRET_KEY=cambia-esto-por-un-secreto-largo
JWT_SECRET_KEY=cambia-esto-por-otro-secreto-largo
```

> **Nota:** la base de datos SQLite (`spectra.db`) se crea automáticamente
> al arrancar el backend. No necesitas instalar nada adicional.

---

## 3. Configurar el frontend

```bash
cd ../frontend
npm install
```

---

## 4. Arrancar backend y frontend

Abre **dos terminales** en la raíz del repositorio.

### Terminal 1 — Backend

```bash
cd backend
source venv/bin/activate        # omite si el entorno ya está activo
uvicorn app.main:app --reload --port 8000
```

El backend queda disponible en `http://localhost:8000`.
La documentación de la API está en `http://localhost:8000/api/docs`.

### Terminal 2 — Frontend

```bash
cd frontend
npm run dev
```

El frontend queda disponible en `http://localhost:3000`.

---

## 5. Inicialización: crear la cuenta de administrador

1. Abre `http://localhost:3000` en el navegador.
2. Al ser la primera ejecución, SPECTRA muestra la pantalla de **configuración inicial**.
3. Introduce email, nombre de usuario y contraseña del administrador y haz clic en **Crear cuenta**.
4. Inicia sesión con las credenciales que acabas de crear.

> La contraseña debe tener al menos 12 caracteres, con mayúscula, minúscula,
> dígito y carácter especial.

---

## 6. Cargar datos de demo (opcional)

Con el backend activo y el entorno virtual activado:

```bash
cd backend
python scripts/seed_demo.py
```

El script crea:
- Pipeline **CorpBot-Internal** (LangChain, 7 nodos, 3 agentes)
- Auditoría **Q2 2026** completada con score crítico (blast radius 81/100)
- 26 eventos de ejecución, persistencia detectada en 3 sesiones

Para crear usuarios de demo adicionales, accede a **Usuarios** en el sidebar
(requiere rol administrador) y usa el botón **Nuevo usuario**.

### Restablecer la base de datos

Si necesitas volver a empezar desde cero:

```bash
cd backend
python scripts/reset_demo.py
```

El script solicita confirmación antes de borrar nada.

---

## 7. Pipeline de laboratorio (opcional)

SPECTRA incluye un pipeline LangChain deliberadamente vulnerable para demo
de prompt injection indirecta.

```bash
cd lab
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python lab_start.py
```

El laboratorio queda disponible en `http://localhost:8001`.
Configura ese URL como endpoint de un pipeline en SPECTRA para auditarlo.

---

## Resumen de URLs

| Servicio             | URL                              |
|----------------------|----------------------------------|
| Aplicación SPECTRA   | http://localhost:3000            |
| API (backend)        | http://localhost:8000/api/v1     |
| Documentación API    | http://localhost:8000/api/docs   |
| Lab (pipeline demo)  | http://localhost:8001            |

---

## Estructura del proyecto

```
SPECTRA/
├── backend/          # API FastAPI (Python 3.11)
│   ├── app/          # Código de la aplicación
│   ├── scripts/      # reset_demo.py, seed_demo.py
│   ├── alembic/      # Migraciones de base de datos
│   └── requirements.txt
├── frontend/         # Interfaz React + Vite
│   └── src/
├── lab/              # Pipeline LangChain vulnerable (demo)
│   └── lab_start.py
└── docker-compose.yml
```

---

## Solución de problemas frecuentes

**`ModuleNotFoundError` al arrancar el backend**
→ Comprueba que el entorno virtual está activo: `source backend/venv/bin/activate`

**`python3` no encontrado en Windows**
→ Usa `python` en lugar de `python3`

**El frontend no conecta con el backend**
→ Verifica que el backend está escuchando en el puerto 8000 y que no hay
cortafuegos bloqueando la conexión local

**La pantalla de setup no aparece**
→ La base de datos ya tiene usuarios. Ejecuta `python scripts/reset_demo.py`
para vaciarla completamente
