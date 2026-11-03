# Application services

Phase 1 implements the LLM provider interface and scoped chat application service.
Only the backend reads credentials. Runtime chat uses the configured real
OpenAI-compatible endpoint; deterministic providers exist only in tests. Later
phases add embedding, retrieval, meeting, memory, search, email and presentation
services. Agents propose effects; application services enforce authorization.
