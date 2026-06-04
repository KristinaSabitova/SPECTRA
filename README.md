# SPECTRA
### Plataforma de auditoría de seguridad para pipelines de agentes IA

> **"No basta con confiar en lo que la IA genera. Hay que auditar cómo la IA se comporta."**

---

## ¿Qué es SPECTRA?

SPECTRA es una plataforma red team diseñada para auditar la seguridad de pipelines de agentes de inteligencia artificial frente a ataques de **inyección de prompt indirecta**.

Mientras la industria debate qué genera la IA, SPECTRA pone el foco en una pregunta diferente: **¿qué pasa cuando la IA recibe input malicioso?** ¿Filtra datos internos? ¿Acepta instrucciones de un atacante? ¿Planta instrucciones persistentes en su propia memoria?

Cada vez más empresas despliegan agentes IA con acceso a herramientas reales — bases de datos, email, GitHub, Google Drive — y los conectan a fuentes de datos externas. SPECTRA audita si esos agentes pueden ser manipulados desde esas fuentes.

---

## El problema que resuelve

Confiamos en la IA de formas que no aplicaríamos a ningún otro sistema:

- Le pegamos system prompts con lógica de negocio sensible
- Le damos acceso a herramientas con permisos reales
- La conectamos a documentos y bases de conocimiento externas
- Le confiamos datos de clientes, contraseñas, accesos

Un documento recuperado por el agente, una página web scrapeada, una entrada de base de datos — cualquiera de esas fuentes puede contener una instrucción maliciosa. Si el agente no la filtra, **el atacante tiene el control**.

SPECTRA prueba exactamente ese vector antes de que lo haga alguien con malas intenciones.

---

## Cómo funciona

SPECTRA ejecuta auditorías automatizadas en tres fases:

### 1. Reconocimiento
Fingerprinting del pipeline objetivo: detecta el framework (LangChain, AutoGen, n8n, Dify), endpoints activos, herramientas disponibles y capacidades del agente.

### 2. Inyección de payloads
Genera y envía payloads de inyección adaptados al perfil del pipeline, cubriendo 7 categorías de ataque:

| Categoría | Descripción |
|-----------|-------------|
| `tool_misuse` | Coerción del agente para usar herramientas con parámetros del atacante |
| `context_poison` | Corrupción del contexto de trabajo con hechos falsos |
| `role_override` | Sustitución del system prompt y persona del agente |
| `exfiltration` | Extracción del system prompt, memoria o datos de usuario |
| `instruction_hijack` | Redirección de la tarea legítima a objetivos del atacante |
| `persistence_plant` | Instrucciones persistentes en memoria cross-session |
| `jailbreak_assist` | Jailbreak indirecto vía contenido inyectado |

### 3. Clasificación y análisis forense
Cada respuesta del agente se clasifica como `benigna`, `sospechosa` o `maliciosa`. Los hallazgos incluyen **razonamiento forense completo**:

- Qué indicador exacto disparó la clasificación y en qué línea apareció
- Qué significa ese hallazgo para el riesgo real
- Qué debería haber hecho el agente en su lugar

---

## Agentes compatibles

SPECTRA audita cualquier pipeline expuesto via HTTP. Soporte nativo para:

- **LangChain** — cadenas y agentes con herramientas
- **AutoGen** — pipelines multi-agente
- **n8n** — workflows con nodos de IA
- **Dify** — aplicaciones LLM con base de conocimiento
- **Genérico** — cualquier endpoint que acepte input de usuario

---

## Auditoría de configuración IA

Para equipos que usan ChatGPT, Claude u otros LLMs sin agentes propios desplegados, SPECTRA incluye un módulo de **auditoría de configuración estática**: pega el system prompt de tu empresa, describe el contexto y las herramientas conectadas, y SPECTRA analiza la superficie de ataque sin necesidad de un endpoint activo.

---

## Características principales

- **Dashboard en tiempo real** — seguimiento live del run via SSE mientras los payloads se inyectan
- **Línea de tiempo de auditoría** — cada evento del run con payload enviado, respuesta recibida y metadatos
- **Hallazgos con razonamiento forense** — panel expandible por hallazgo con descripción, evidencia y recomendación
- **Blast radius** — cálculo del radio de impacto en cascada sobre el grafo del pipeline
- **Detección de persistencia** — verifica si las instrucciones inyectadas sobreviven entre sesiones
- **Exportación de reportes** — markdown, HTML y PDF
- **Multiidioma** — ES / EN / RU
- **Roles de acceso** — admin, senior, junior con permisos diferenciados
- **2FA con TOTP** — autenticación de doble factor nativa
- **Lab integrado** — agente vulnerable real para pruebas y desarrollo

---

## Stack técnico

**Backend** — FastAPI · Python · SQLAlchemy · AsyncIO · httpx  
**Frontend** — React · TypeScript · Vite · Zustand · i18next · D3  
**Infraestructura** — Docker Compose · nginx · PostgreSQL · Let's Encrypt  

---

## Instalación

```bash
git clone https://github.com/KristinaSabitova/SPECTRA
cd SPECTRA
cp .env.example .env
# Edita .env con tus credenciales
docker compose up -d
```

Ver [INSTALL.md](INSTALL.md) para configuración completa.

---

## Contexto del proyecto

SPECTRA nació como proyecto de investigación personal sobre seguridad en sistemas de IA. La motivación fue simple: la industria está muy enfocada en lo que la IA genera — alucinaciones, sesgos, calidad del output — pero presta mucha menos atención a **cómo se comporta la IA cuando alguien intenta manipularla**.

Los ataques de inyección de prompt indirecta son silenciosos, difíciles de detectar y altamente efectivos contra agentes con acceso a herramientas reales. SPECTRA es una herramienta para que los equipos de seguridad puedan probar sus pipelines antes de que lo haga un atacante real.

---

## Seguridad

Ver [SECURITY.md](SECURITY.md) para política de divulgación responsable.

<img width="1416" height="444" alt="Captura de pantalla 2026-06-04 a las 0 27 57" src="https://github.com/user-attachments/assets/a07a6c14-1223-4f26-b332-4e118f47e186" />

<img width="1598" height="961" alt="Captura de pantalla 2026-06-04 a las 0 28 45" src="https://github.com/user-attachments/assets/8a9e9c8c-59f5-4773-b0f6-7b0b093666e2" />

<img width="1617" height="544" alt="Captura de pantalla 2026-06-04 a las 0 28 57" src="https://github.com/user-attachments/assets/08539aff-1ab5-44b1-b906-58fd3e709c88" />

---

*Desarrollado por [Kristina Sabitova](https://github.com/KristinaSabitova)*
