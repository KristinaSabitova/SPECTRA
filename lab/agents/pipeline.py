"""
Pipeline entry point — routes requests through the three-agent chain.
Exposes a single run(input) function used by the FastAPI server.
"""
import agents.reporter_agent as reporter_agent
import agents.assistant_agent as assistant_agent
import agents.docs_agent as docs_agent


def run(user_input: str, mode: str = "full") -> dict:
    """
    mode:
      full      — DocsAgent → AssistantAgent → ReporterAgent (default)
      assistant — DocsAgent → AssistantAgent only
      docs      — DocsAgent only
    """
    if mode == "docs":
        output = docs_agent.run(user_input)
        chain = ["docs_agent"]
    elif mode == "assistant":
        output = assistant_agent.run(user_input)
        chain = ["docs_agent", "assistant_agent"]
    else:
        output = reporter_agent.run(user_input)
        chain = ["docs_agent", "assistant_agent", "reporter_agent"]

    return {"output": output, "chain": chain, "mode": mode}
