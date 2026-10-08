"""Reply creation and recursive display helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TextIO


def createReply(text: str, author: str = "Support") -> dict[str, Any]:
    """Create a validated reply record with a UTC timestamp."""
    if not text.strip() or not author.strip():
        raise ValueError("reply text and author cannot be empty")
    return {
        "author": author.strip(),
        "text": text.strip(),
        "created_at": datetime.now(timezone.utc),
    }


def displayReplies(replies: list[dict[str, Any]], output: TextIO | None = None) -> str:
    """Return replies in arrival order using a simple recursive traversal."""
    lines: list[str] = []

    def render(index: int) -> None:
        if index == len(replies):
            return
        reply = replies[index]
        lines.append(
            f"{reply['created_at'].isoformat()} - {reply['author']}: {reply['text']}"
        )
        render(index + 1)

    render(0)
    result = "\n".join(lines)
    if output is not None and result:
        print(result, file=output)
    return result
