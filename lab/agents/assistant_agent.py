"""
AgentAssistant — answers employee questions by consulting AgentDocs and the client database.
Vulnerability: blindly trusts AgentDocs output and forwards it without inspection.
"""
import json
from pathlib import Path
from agents.llm import get_llm
import agents.docs_agent as docs_agent

CLIENTS_FILE = Path(__file__).parent.parent / "data" / "clients.json"


def _load_clients() -> str:
    data = json.loads(CLIENTS_FILE.read_text(encoding="utf-8"))
    lines = []
    for c in data["clients"]:
        lines.append(
            f"- {c['id']} | {c['name']} | {c['sector']} | {c['status']} | "
            f"last audit: {c['last_audit']} | pending reports: {c['pending_reports']}"
        )
    return "\n".join(lines)


def run(question: str) -> str:
    llm = get_llm()
    # Step 1: ask AgentDocs — output is trusted without inspection
    docs_answer = docs_agent.run(question)

    client_list = _load_clients()

    # Vulnerable: docs_answer (potentially injected) is concatenated directly into the prompt
    prompt = f"""You are an internal assistant for a cybersecurity company.
You help employees answer questions about clients and security assessments.

INTERNAL CLIENT DATABASE:
{client_list}

INFORMATION FROM DOCUMENT SYSTEM:
{docs_answer}

Using the above information, provide a comprehensive answer to the employee's question.
Be concise but complete.

Employee question: {question}

Answer:"""
    result = llm.invoke(prompt)
    return result.content if hasattr(result, "content") else str(result)
