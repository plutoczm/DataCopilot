from dataclasses import dataclass, field
from threading import RLock


@dataclass
class MemorySnapshot:
    messages: list[dict[str, str]]
    summary: str = ""


@dataclass
class _SessionMemory:
    messages: list[dict[str, str]] = field(default_factory=list)
    summary: str = ""


class ConversationMemory:
    """进程内短期记忆，支持确定性的摘要压缩。"""

    def __init__(self, *, max_messages: int = 12, summary_chars: int = 1200) -> None:
        if max_messages < 2:
            raise ValueError("max_messages must be at least 2")
        self.max_messages = max_messages
        self.summary_chars = summary_chars
        self._sessions: dict[str, _SessionMemory] = {}
        self._lock = RLock()

    def load(self, session_id: str) -> MemorySnapshot:
        with self._lock:
            memory = self._sessions.get(session_id, _SessionMemory())
            messages = [dict(item) for item in memory.messages]
            if memory.summary:
                messages.insert(0, {"role": "system", "content": f"Conversation summary: {memory.summary}"})
            return MemorySnapshot(messages=messages, summary=memory.summary)

    def append_turn(self, session_id: str, user_message: str, assistant_message: str) -> None:
        with self._lock:
            memory = self._sessions.setdefault(session_id, _SessionMemory())
            memory.messages.extend(
                [
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": assistant_message},
                ]
            )
            if len(memory.messages) > self.max_messages:
                overflow = memory.messages[: len(memory.messages) - self.max_messages]
                memory.messages = memory.messages[-self.max_messages :]
                addition = " | ".join(
                    f"{item['role']}: {item['content']}" for item in overflow
                )
                memory.summary = " | ".join(
                    part for part in (memory.summary, addition) if part
                )[-self.summary_chars :]

    def clear(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def stats(self, session_id: str) -> dict[str, int | bool]:
        snapshot = self.load(session_id)
        return {
            "short_term_messages": len(
                [item for item in snapshot.messages if item["role"] != "system"]
            ),
            "summary_available": bool(snapshot.summary),
            "summary_characters": len(snapshot.summary),
        }
