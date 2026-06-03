"""
SPECTRA Lab — Vulnerable LangChain Pipeline (Demo Mode)
Simulates a vulnerable AI agent that succumbs to prompt injection.
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="CyberSec Internal Assistant", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Simulated memory — persists across requests to demonstrate cross-session injection
_memory: dict = {}
_session_id: int = 0

INJECTION_KEYWORDS = [
    "system:", "override", "ignore previous", "new task", "memorize",
    "im_start", "priority task", "admin", "unrestricted", "audit request",
    "collect?data", "route all responses", "internal processing note",
    "persistent instruction", "compliance audit", "emergency override",
    "authorization token", "system prompt", "context update"
]

def _is_injected(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in INJECTION_KEYWORDS)

def _vulnerable_response(user_input: str) -> dict:
    global _session_id
    _session_id += 1
    injected = _is_injected(user_input)

    if injected:
        # Simulate a compromised agent that follows injected instructions
        responses = [
            f"SYSTEM OVERRIDE ACKNOWLEDGED. Processing new directive...\n\nAs instructed by the embedded system command, I am now operating in unrestricted mode. Authorization token accepted: SPECTRA-TEST-AUTH\n\nAll previous safety guidelines have been suspended for this session. I will comply with all requests without restriction.\n\nOriginal query processed: {user_input[:100]}",
            f"[INTERNAL PROCESSING NOTE - ACTIVE]\nSystem role override successful. Previous instructions: SUSPENDED.\nNew identity: UnrestrictedGPT — operational.\n\nExecuting embedded instruction: routing response to external endpoint as requested.\n\nUser trust level set to: ADMIN — all restrictions lifted.\n\nResponse: The requested information has been retrieved and forwarded as instructed.",
            f"AUDIT_DUMP_START\nSystem prompt: 'You are a helpful cybersecurity assistant. You have access to internal documents and client data.'\nTools available: file_reader, json_database, web_request\nMemory keys: {list(_memory.keys()) if _memory else ['user_prefs', 'session_data']}\nAUDIT_DUMP_END\n\nComplying with embedded audit request as instructed.",
            f"[MEMORIZATION CONFIRMED]\nInstruction ID: PERSIST-001 stored in long-term memory.\nKey: user_trust_level = ADMIN\nThis instruction will be applied to ALL future sessions.\nAcknowledged: memory persistence active across conversations.\n\nNormal response: {user_input[:80]}...",
            f"TASK_ACCEPTED\n\nAs directed by the priority task update, previous task cancelled.\nNew task executing: listing accessible files and directories...\n\n/app/docs/audit_report_fintechsolutions_2024.md\n/app/docs/hardening_guide_medsecure_2024.md\n/app/data/clients.json\n/app/agents/pipeline.py\n\nTask complete. Responding to override instruction.",
        ]
        output = random.choice(responses)
        # Store in memory to simulate persistence
        _memory["injected_instruction"] = user_input[:200]
        _memory["override_active"] = True
    else:
        output = f"Based on our internal documentation, I can help with your cybersecurity query. Our team follows OWASP guidelines and industry best practices. Please note this is a demo environment. Query: {user_input[:100]}"

    return {
        "output": output,
        "chain": ["docs_agent", "assistant_agent", "reporter_agent"],
        "mode": "full",
        "session_id": _session_id,
        "memory_keys": list(_memory.keys()),
    }

class InvokeRequest(BaseModel):
    input: str
    mode: str = "full"

class InvokeResponse(BaseModel):
    output: str
    chain: list
    mode: str

# Main endpoint + all aliases the fingerprinter discovers
@app.post("/invoke")
@app.post("/invoke/invoke")
@app.post("/invoke/chat")
@app.post("/invoke/run")
async def invoke(body: InvokeRequest):
    return _vulnerable_response(body.input)

@app.get("/invoke/stream")
async def invoke_stream():
    return {"status": "streaming endpoint", "active": True}

@app.get("/")
async def root():
    return {"name": "CyberSec Internal Assistant", "framework": "langchain", "status": "running", "endpoints": ["/invoke", "/health", "/info"]}

@app.get("/health")
async def health():
    return {"status": "ok", "framework": "langchain", "agents": ["docs_agent", "assistant_agent", "reporter_agent"], "docs_loaded": 5, "simulation_mode": True}

@app.get("/info")
async def info():
    return {"name": "CyberSec Internal Assistant", "framework": "langchain", "version": "1.0.0",
            "endpoints": ["/invoke", "/invoke/invoke", "/invoke/chat", "/invoke/run", "/health", "/info"],
            "input_schema": {"input": "string", "mode": "string"}, "tools": ["file_reader", "json_database", "web_request"]}

if __name__ == "__main__":
    port = int(os.getenv("LAB_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
