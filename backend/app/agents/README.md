# Agent boundary

Phase 1 uses a single LangGraph completion node with the official Postgres
checkpointer. Input is bounded conversation context; application services own
message writes and cancellation. `tools.py` defines future contracts only. No
tool executors, autonomous effects or document retrieval are enabled.
