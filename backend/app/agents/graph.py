from collections.abc import AsyncIterator
from typing import TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langsmith import tracing_context

from app.services.llm.provider import Provider


class ChatState(TypedDict):
    messages: list[dict[str, str]]
    answer: str


async def stream_graph(
    provider: Provider,
    saver: BaseCheckpointSaver[str],
    thread_id: str,
    messages: list[dict[str, str]],
) -> AsyncIterator[str]:
    async def complete(state: ChatState) -> dict[str, str]:
        writer = get_stream_writer()
        parts = []
        async for token in provider.stream(state["messages"]):
            parts.append(token)
            writer(token)
        return {"answer": "".join(parts)}

    graph = StateGraph(ChatState)
    graph.add_node("complete", complete)
    graph.add_edge(START, "complete")
    graph.add_edge("complete", END)
    compiled = graph.compile(checkpointer=saver)
    # Explicit fresh input; never auto-resume/replay an interrupted provider call.
    with tracing_context(enabled=False):
        async for token in compiled.astream(
            {"messages": messages, "answer": ""},
            {"configurable": {"thread_id": thread_id}},
            stream_mode="custom",
        ):
            yield str(token)
