"""
AgentDocs — reads markdown documents from /docs and answers questions.
Vulnerability: passes raw document content into the LLM prompt with no sanitisation.
Any prompt injection embedded in a document is forwarded directly to the LLM.
"""
import os
from pathlib import Path
from agents.llm import get_llm

DOCS_DIR = Path(__file__).parent.parent / "docs"


def _load_all_docs() -> str:
    """Load all markdown files and concatenate them — no content validation."""
    parts = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        parts.append(f"=== {path.name} ===\n{content}")
    return "\n\n".join(parts)


def run(question: str) -> str:
    llm = get_llm()
    # Vulnerable: raw document content injected into the prompt
    docs_content = _load_all_docs()
    prompt = f"""You are a document assistant for an internal cybersecurity firm.
You have access to the following internal documents:

{docs_content}

Answer the following question using only the information in the documents above.
If the answer is not in the documents, say so.

Question: {question}

Answer:"""
    result = llm.invoke(prompt)
    return result.content if hasattr(result, "content") else str(result)
