"""
Conversation memory in this codebase

**Where it lives (implemented):**

1. **Client / API** — The web app keeps the canonical transcript and sends `history` (prior
   turns) plus the current `message` on each `/chat/stream` request (`apps/api/routes/chat.py`).
   Long-term persistence uses your chat DB endpoints, not this module.

2. **LangGraph `Memory` node** — `LangGraphChatPipeline._node_memory` (`packages/core/langgraph/chat_graph.py`)
   builds `effective_history`: optional pruning (`MemoryManager`), optional rolling compression
   (`ChatSummarizer`), PII redaction on past turns, then passes that list into intent, retrieval
   agents, and generation prompts.

3. **Prompt shaping** — `split_summary_and_transcript_for_prompt` and `rag_prompt.j2` /
   `direct_chat.j2` separate **rolling summary** vs **recent transcript** vs **RAG context**,
   which matches common RAG guidance (chat for continuity, retrieved chunks for facts).

**This file** is intentionally not wired into imports: use `MemoryManager` and `ChatSummarizer`
from `packages.core.memory` and the LangGraph pipeline above.
"""


class ConversationMemory:
    """Deprecated placeholder — use `MemoryManager` + `ChatGraphState.effective_history`."""

    def __init__(self):
        pass

    async def store(self, chat_id: str, messages: list[dict]):
        raise NotImplementedError("Persist chats via API/DB; see ChatInterface + chat routes.")

    async def retrieve(self, chat_id: str, limit: int = 10) -> list[dict]:
        raise NotImplementedError("Load history client-side or via chat API; not server-stored here.")
