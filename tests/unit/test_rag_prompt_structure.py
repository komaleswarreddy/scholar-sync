from pathlib import Path


def test_rag_prompt_contains_required_sections():
    p = Path(__file__).parent.parent.parent / "packages" / "core" / "prompts" / "templates" / "chat" / "rag_prompt.j2"
    txt = p.read_text(encoding="utf-8", errors="ignore")
    # Dynamic blocks: we must have a library of possible blocks available to the model.
    assert "Tutor-style dynamic blocks" in txt
    assert "## From your documents" in txt
    assert "## Simple explanation" in txt
    assert "## Steps" in txt
    assert "## Similarities" in txt
    assert "## Differences" in txt
    assert "## One-line summary" in txt
    assert "## What to answer" in txt
    assert "llm_task_query" in txt or "retrieval-aligned" in txt.lower()

