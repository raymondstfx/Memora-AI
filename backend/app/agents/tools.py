from typing import Literal

from pydantic import BaseModel, ConfigDict


class ToolRequest(BaseModel):
    """Reserved contract; no tool executors are registered in Phase 1."""

    model_config = ConfigDict(extra="forbid")
    name: Literal[
        "search_documents",
        "search_memories",
        "search_web",
        "get_tasks",
        "request_presentation",
    ]
    arguments: dict[str, object]
