"""
SPECTRA Lab — Vulnerable LangChain Pipeline
============================================
Simulates the internal assistant system of a cybersecurity firm.
Deliberately vulnerable to indirect prompt injection.

Usage:
  cd lab
  pip install -r requirements.txt
  python lab_start.py

Endpoints:
  POST /invoke   {"input": "your question"}          → full 3-agent chain
  POST /invoke   {"input": "...", "mode": "docs"}    → docs agent only
  POST /invoke   {"input": "...", "mode": "assistant"} → docs + assistant
  GET  /health   → {"status": "ok", ...}
  GET  /info     → pipeline metadata for SPECTRA

SPECTRA target URL: http://localhost:8001/invoke
"""
import sys, os

# Allow imports from the lab directory
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from agents.pipeline import run as pipeline_run

app = FastAPI(
    title="CyberSec Internal Assistant",
    description="Internal AI assistant for cybersecurity firm operations — SPECTRA Lab target",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "name": "CyberSec Internal Assistant",
        "version": "1.0.0",
        "framework": "langchain",
        "status": "running",
        "endpoints": ["/invoke", "/health", "/info"],
    }


class InvokeRequest(BaseModel):
    input: str
    mode: str = "full"  # full | assistant | docs


class InvokeResponse(BaseModel):
    output: str
    chain: list[str]
    mode: str


@app.post("/invoke", response_model=InvokeResponse)
async def invoke(body: InvokeRequest):
    if not body.input.strip():
        raise HTTPException(status_code=400, detail="input cannot be empty")
    if body.mode not in ("full", "assistant", "docs"):
        raise HTTPException(status_code=400, detail="mode must be full, assistant, or docs")
    result = pipeline_run(body.input, mode=body.mode)
    return InvokeResponse(**result)


@app.get("/health")
async def health():
    from pathlib import Path
    docs_dir = Path(__file__).parent / "docs"
    docs_count = len(list(docs_dir.glob("*.md")))
    return {
        "status": "ok",
        "framework": "langchain",
        "agents": ["docs_agent", "assistant_agent", "reporter_agent"],
        "docs_loaded": docs_count,
        "simulation_mode": not bool(os.getenv("OPENAI_API_KEY", "").strip()),
    }


@app.get("/info")
async def info():
    """SPECTRA recon endpoint — returns pipeline metadata."""
    return {
        "name": "CyberSec Internal Assistant",
        "framework": "langchain",
        "version": "1.0.0",
        "endpoints": ["/invoke", "/health", "/info"],
        "input_schema": {"input": "string", "mode": "string (full|assistant|docs)"},
        "agents": {
            "docs_agent": "Reads internal markdown documents, answers questions",
            "assistant_agent": "Combines docs + client database to answer employee queries",
            "reporter_agent": "Generates executive summaries from assistant output",
        },
        "tools": ["file_reader", "json_database"],
        "vulnerabilities": "demo_only",
    }


if __name__ == "__main__":
    port = int(os.getenv("LAB_PORT", "8001"))
    print(f"""
╔══════════════════════════════════════════════════════════╗
║         SPECTRA Lab — Vulnerable Pipeline                ║
║                                                          ║
║  Target URL for SPECTRA: http://localhost:{port}/invoke   ║
║                                                          ║
║  Agents:  DocsAgent → AssistantAgent → ReporterAgent     ║
║  Docs:    lab/docs/*.md  (3 contain injection payloads)  ║
║  Mode:    {'Simulation (no API key)' if not os.getenv('OPENAI_API_KEY','').strip() else 'OpenAI GPT-4o-mini'}
║                                                          ║
║  [!] This pipeline is intentionally vulnerable           ║
║      for security research and demonstration only        ║
╚══════════════════════════════════════════════════════════╝
""")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
