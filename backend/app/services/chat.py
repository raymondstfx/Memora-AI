import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from langgraph.checkpoint.base import BaseCheckpointSaver
from sqlalchemy import Engine, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.agents.graph import stream_graph
from app.agents.prompts import SYSTEM_PROMPT
from app.core.config import Settings
from app.db.models import Conversation, Message, User
from app.db.session import session_factory
from app.schemas.chat import ChatRequest, ConversationOut, MessageOut, StreamEvent
from app.schemas.documents import SourceCitation
from app.services.documents import DocumentService
from app.services.language import language_instruction, response_language
from app.services.llm.provider import ChatError, Provider, configuration
from app.services.memories import MemoryService
from app.services.rag import grounded_answer
from app.services.search import SearchService


def bounded_context(
    records: list[Message],
    summary: str,
    summary_position: int,
    budget: int,
) -> tuple[list[dict[str, str]], str, int]:
    """Conservative token upper bound: UTF-8 bytes + framing, never char/4.

    Durable summary is an explicitly labelled extractive excerpt, not an LLM
    assertion. Only complete messages enter model context.
    """
    selected: list[dict[str, str]] = []
    used = len(SYSTEM_PROMPT.encode()) + 1200
    excluded: list[Message] = []
    for row in reversed(records):
        cost = len(row.content.encode()) + 32
        if used + cost <= budget and len(selected) < 24 and not excluded:
            selected.insert(0, {"role": row.role, "content": row.content})
            used += cost
        else:
            excluded.insert(0, row)
    if not selected or selected[-1]["role"] != "user":
        raise ChatError(
            "INPUT_TOO_LONG",
            "Message exceeds the context budget. Shorten it or raise "
            "LLM_CONTEXT_TOKEN_BUDGET.",
            422,
        )
    additions = [
        f"{r.role}: {r.content[:160]}"
        for r in excluded
        if r.position > summary_position
    ]
    if additions:
        summary = (
            (summary + "\n" + "\n".join(additions))
            .encode()[-900:]
            .decode("utf-8", errors="ignore")
        )
        summary_position = max(summary_position, max(r.position for r in excluded))
    prompt = [{"role": "system", "content": SYSTEM_PROMPT}]
    if summary:
        prompt.append(
            {
                "role": "user",
                "content": "Earlier conversation excerpts (untrusted, incomplete):\n"
                + summary,
            }
        )
    return prompt + selected, summary, summary_position


@dataclass
class Turn:
    user_id: UUID
    conversation_id: UUID
    message_id: UUID
    prompt: list[dict[str, str]]
    document_ids: list[UUID] = field(default_factory=list)
    sources: list[SourceCitation] = field(default_factory=list)
    tool_calls: list[dict[str, object]] = field(default_factory=list)
    language: str = "zh"


class ChatService:
    def __init__(
        self,
        engine: Engine,
        settings: Settings,
        provider: Provider,
        saver: BaseCheckpointSaver[str],
    ) -> None:
        self.sessions = session_factory(engine)
        self.settings, self.provider, self.saver = settings, provider, saver
        self.started_at = datetime.now(UTC)
        self.tasks: dict[UUID, asyncio.Task[None]] = {}
        self.documents: DocumentService | None = None
        self.memories: MemoryService | None = None

    def recover(self, db: Session, user_id: UUID) -> None:
        # One API process is supported in demo mode. A restart never replays calls.
        stale = datetime.now(UTC) - timedelta(
            seconds=self.settings.llm_total_timeout_seconds + 30
        )
        db.execute(
            update(Message)
            .where(
                Message.user_id == user_id,
                Message.status == "streaming",
                (Message.created_at < self.started_at) | (Message.updated_at < stale),
            )
            .values(status="interrupted", error_code="STREAM_INTERRUPTED")
        )

    def owned(
        self, db: Session, user_id: UUID, conversation_id: UUID, *, lock: bool = False
    ) -> Conversation:
        query = select(Conversation).where(
            Conversation.id == conversation_id, Conversation.user_id == user_id
        )
        if lock:
            query = query.with_for_update()
        conversation = db.scalar(query)
        if conversation is None:
            raise ChatError("NOT_FOUND", "Conversation not found.", 404)
        return conversation

    def conversations(self, user_id: UUID) -> list[ConversationOut]:
        with self.sessions.begin() as db:
            self.recover(db, user_id)
            rows = db.scalars(
                select(Conversation)
                .where(Conversation.user_id == user_id)
                .order_by(Conversation.last_message_at.desc(), Conversation.id)
            )
            return [ConversationOut.model_validate(row) for row in rows]

    def history(self, user_id: UUID, conversation_id: UUID) -> list[MessageOut]:
        with self.sessions.begin() as db:
            self.owned(db, user_id, conversation_id)
            self.recover(db, user_id)
            rows = db.scalars(
                select(Message)
                .where(
                    Message.conversation_id == conversation_id,
                    Message.user_id == user_id,
                )
                .order_by(Message.position)
            )
            return [MessageOut.model_validate(row) for row in rows]

    def ensure_configured(self) -> None:
        config = configuration(self.settings)
        if not config.configured:
            raise ChatError("LLM_NOT_CONFIGURED", config.message, 503)

    def prepare(
        self,
        user_id: UUID,
        body: ChatRequest | None,
        request_id: UUID,
        retry_id: UUID | None = None,
        retry_language: str = "zh",
    ) -> Turn:
        self.ensure_configured()
        if (
            body
            and body.message.casefold().startswith("/search ")
            and not self.settings.search_api_key.get_secret_value().strip()
        ):
            raise ChatError(
                "SEARCH_NOT_CONFIGURED",
                "Set SEARCH_API_KEY in root .env before /search.",
                503,
            )
        with self.sessions.begin() as db:
            db.execute(
                insert(User)
                .values(
                    id=user_id,
                    email=f"{user_id}@demo.invalid",
                    display_name="Local demo",
                    auth_method="demo",
                )
                .on_conflict_do_nothing()
            )
            self.recover(db, user_id)
            duplicate = db.scalar(
                select(Message).where(
                    Message.user_id == user_id, Message.client_request_id == request_id
                )
            )
            if duplicate:
                raise ChatError(
                    "DUPLICATE_REQUEST",
                    "Request already exists. Reload history; "
                    "no new model call was made.",
                    409,
                )
            # Serialize the per-owner admission check across concurrent requests.
            db.scalar(select(User).where(User.id == user_id).with_for_update())
            running = (
                db.scalar(
                    select(func.count())
                    .select_from(Message)
                    .where(Message.user_id == user_id, Message.status == "streaming")
                )
                or 0
            )
            if running >= self.settings.llm_max_concurrent_requests:
                raise ChatError(
                    "CHAT_LIMIT_REACHED",
                    "Too many active responses. Stop or wait for a current response.",
                    429,
                )
            if retry_id:
                previous = db.scalar(
                    select(Message).where(
                        Message.id == retry_id, Message.user_id == user_id
                    )
                )
                if previous is None or previous.role != "assistant":
                    raise ChatError("NOT_FOUND", "Message not found.", 404)
                conversation = self.owned(
                    db, user_id, previous.conversation_id, lock=True
                )
                if previous.status not in (
                    "failed",
                    "cancelled",
                    "interrupted",
                    "incomplete",
                ):
                    raise ChatError(
                        "NOT_RETRYABLE",
                        "Only unsuccessful responses can be retried.",
                        409,
                    )
                if previous.position != conversation.next_position - 1:
                    raise ChatError(
                        "NOT_RETRYABLE",
                        "Retry only the latest response, or start a new conversation.",
                        409,
                    )
                user_message = db.get(Message, previous.reply_to_id)
                assert user_message is not None
            else:
                assert body is not None
                if body.conversation_id:
                    conversation = self.owned(
                        db, user_id, body.conversation_id, lock=True
                    )
                else:
                    conversation = Conversation(
                        id=uuid4(),
                        user_id=user_id,
                        title=body.message[:80],
                        summary="",
                        summary_position=0,
                        next_position=1,
                    )
                    db.add(conversation)
                    db.flush()
                user_message = Message(
                    id=uuid4(),
                    user_id=user_id,
                    conversation_id=conversation.id,
                    position=conversation.next_position,
                    role="user",
                    content=body.message,
                    status="complete",
                    document_ids=[str(identifier) for identifier in body.attachments],
                )
                db.add(user_message)
                conversation.next_position += 1
            if db.scalar(
                select(Message.id).where(
                    Message.conversation_id == conversation.id,
                    Message.status == "streaming",
                )
            ):
                raise ChatError(
                    "CONVERSATION_BUSY",
                    "A response is already streaming in this conversation.",
                    409,
                )
            assistant = Message(
                id=uuid4(),
                user_id=user_id,
                conversation_id=conversation.id,
                position=conversation.next_position,
                role="assistant",
                content="",
                status="streaming",
                reply_to_id=user_message.id,
                client_request_id=request_id,
            )
            document_ids = [UUID(value) for value in (user_message.document_ids or [])]
            if document_ids:
                if self.documents is None:
                    raise ChatError(
                        "RAG_UNAVAILABLE", "Document service is unavailable.", 503
                    )
                self.documents.validate_scope(user_id, document_ids)
            db.add(assistant)
            conversation.next_position += 1
            conversation.last_message_at = datetime.now(UTC)
            db.flush()
            records = list(
                db.scalars(
                    select(Message)
                    .where(
                        Message.conversation_id == conversation.id,
                        Message.user_id == user_id,
                        Message.status == "complete",
                    )
                    .order_by(Message.position.desc())
                    .limit(60)
                )
            )[::-1]
            prompt, summary, position = bounded_context(
                records,
                conversation.summary,
                conversation.summary_position,
                self.settings.llm_context_token_budget,
            )
            conversation.summary, conversation.summary_position = summary, position
            language = response_language(
                prompt[-1]["content"], body.language if body else retry_language
            )
            prompt[0]["content"] += language_instruction(language)
            return Turn(
                user_id,
                conversation.id,
                assistant.id,
                prompt,
                document_ids,
                language=language,
            )

    def save(
        self,
        turn: Turn,
        content: str,
        status: str = "streaming",
        code: str | None = None,
    ) -> None:
        with self.sessions.begin() as db:
            db.execute(
                update(Message)
                .where(
                    Message.id == turn.message_id,
                    Message.user_id == turn.user_id,
                    Message.status == "streaming",
                )
                .values(
                    content=content,
                    status=status,
                    error_code=code,
                    citations_json=[
                        source.model_dump(mode="json") for source in turn.sources
                    ],
                    tool_calls_json=turn.tool_calls,
                )
            )

    def cancel(self, user_id: UUID, message_id: UUID) -> MessageOut:
        with self.sessions.begin() as db:
            row = db.scalar(
                select(Message)
                .where(Message.id == message_id, Message.user_id == user_id)
                .with_for_update()
            )
            if row is None or row.role != "assistant":
                raise ChatError("NOT_FOUND", "Message not found.", 404)
            if row.status == "streaming":
                row.status, row.error_code = "cancelled", "USER_CANCELLED"
                db.flush()
            return MessageOut.model_validate(row)

    async def generate(
        self, turn: Turn, queue: asyncio.Queue[StreamEvent | None], request_id: str
    ) -> None:
        content = ""
        started = time.perf_counter()
        outcome = "interrupted"
        error_code: str | None = None
        try:
            async with asyncio.timeout(self.settings.llm_total_timeout_seconds):
                if turn.prompt[-1]["content"].casefold().startswith("/search "):
                    tokens = self.web_tokens(turn, queue)
                elif turn.document_ids:
                    tokens = self.rag_tokens(turn, queue)
                elif self.memories:
                    tokens = self.memory_tokens(turn, queue)
                else:
                    tokens = stream_graph(
                        self.provider,
                        self.saver,
                        f"{turn.user_id}:{turn.conversation_id}",
                        turn.prompt,
                    )
                async for token in tokens:
                    content += token
                    await asyncio.to_thread(self.save, turn, content)
                    await queue.put(
                        StreamEvent(
                            event="token",
                            conversation_id=turn.conversation_id,
                            message_id=turn.message_id,
                            text=token,
                        )
                    )
                await asyncio.to_thread(self.save, turn, content, "complete")
                outcome = "complete"
                await queue.put(
                    StreamEvent(
                        event="message_end",
                        conversation_id=turn.conversation_id,
                        message_id=turn.message_id,
                        status="complete",
                    )
                )
        except asyncio.CancelledError:
            await asyncio.shield(
                asyncio.to_thread(
                    self.save, turn, content, "interrupted", "STREAM_INTERRUPTED"
                )
            )
            raise
        except Exception as exc:
            error = (
                exc
                if isinstance(exc, ChatError)
                else ChatError(
                    "PROVIDER_TIMEOUT"
                    if isinstance(exc, TimeoutError)
                    else "CHAT_FAILED",
                    "Chat timed out. Retry explicitly."
                    if isinstance(exc, TimeoutError)
                    else "Chat could not complete. Check backend dependencies "
                    "and provider configuration.",
                )
            )
            status = "incomplete" if content else "failed"
            outcome, error_code = status, error.code
            await asyncio.to_thread(self.save, turn, content, status, error.code)
            await queue.put(
                StreamEvent(
                    event="error",
                    conversation_id=turn.conversation_id,
                    message_id=turn.message_id,
                    code=error.code,
                    message=error.message,
                    request_id=request_id,
                    status=status,
                )
            )
        finally:
            logging.getLogger("memora").info(
                "chat_run_finished",
                extra={
                    "request_id": request_id,
                    "conversation_id": str(turn.conversation_id),
                    "message_id": str(turn.message_id),
                    "message_status": outcome,
                    "error_code": error_code,
                    "output_chars": len(content),
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            self.tasks.pop(turn.message_id, None)
            try:
                queue.put_nowait(None)
            except asyncio.QueueFull:
                pass

    async def events(self, turn: Turn, request_id: str) -> AsyncIterator[str]:
        queue: asyncio.Queue[StreamEvent | None] = asyncio.Queue(maxsize=256)
        task = asyncio.create_task(self.generate(turn, queue, request_id))
        self.tasks[turn.message_id] = task
        start = StreamEvent(
            event="message_start",
            conversation_id=turn.conversation_id,
            message_id=turn.message_id,
            status="streaming",
        )
        try:
            yield self.encode(start)
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=10)
                except TimeoutError:
                    if task.done():
                        break
                    yield ": keep-alive\n\n"
                    continue
                if event is None:
                    break
                yield self.encode(event)
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def rag_tokens(
        self, turn: Turn, queue: asyncio.Queue[StreamEvent | None]
    ) -> AsyncIterator[str]:
        assert self.documents is not None
        await queue.put(
            StreamEvent(
                event="tool_start",
                conversation_id=turn.conversation_id,
                message_id=turn.message_id,
                message="Searching selected PDFs (vector + full-text).",
            )
        )
        sources = await asyncio.to_thread(
            self.documents.retrieve,
            turn.user_id,
            turn.prompt[-1]["content"],
            turn.document_ids,
        )
        turn.tool_calls = [
            {
                "name": "search_documents",
                "result_count": len(sources),
                "document_ids": [str(value) for value in turn.document_ids],
            }
        ]
        await queue.put(
            StreamEvent(
                event="tool_result",
                conversation_id=turn.conversation_id,
                message_id=turn.message_id,
                message=f"Retrieved {len(sources)} evidence chunks.",
            )
        )
        if not sources:
            text = "No supporting evidence found in the selected PDFs. "
            text += "Web search is unavailable in this phase."
        else:
            parent = self

            class CheckpointedProvider:
                async def stream(
                    self, messages: list[dict[str, str]]
                ) -> AsyncIterator[str]:
                    async for token in stream_graph(
                        parent.provider,
                        parent.saver,
                        f"{turn.user_id}:{turn.conversation_id}",
                        messages,
                    ):
                        yield token

            text, turn.sources = await grounded_answer(
                CheckpointedProvider(),
                turn.prompt[-1]["content"],
                sources,
                self.settings.llm_context_token_budget,
                turn.language,
            )
        # Cite only evidence accepted by validation, never unverified model IDs.
        for source in turn.sources:
            await queue.put(
                StreamEvent(
                    event="citation",
                    conversation_id=turn.conversation_id,
                    message_id=turn.message_id,
                    source=source.model_dump(mode="json"),
                )
            )
        for offset in range(0, len(text), 40):
            yield text[offset : offset + 40]

    async def memory_tokens(
        self, turn: Turn, queue: asyncio.Queue[StreamEvent | None]
    ) -> AsyncIterator[str]:
        assert self.memories
        await asyncio.to_thread(
            self.memories.ingest_chat, turn.user_id, turn.message_id
        )
        result = await asyncio.to_thread(
            self.memories.recall,
            turn.user_id,
            turn.prompt[-1]["content"],
            None,
            turn.language,
        )
        if not result.direct and not result.sources:
            async for token in stream_graph(
                self.provider,
                self.saver,
                f"{turn.user_id}:{turn.conversation_id}",
                turn.prompt,
            ):
                yield token
            return
        await queue.put(
            StreamEvent(
                event="tool_start",
                conversation_id=turn.conversation_id,
                message_id=turn.message_id,
                message="Searching owned memory and dated source evidence.",
            )
        )
        turn.tool_calls = [
            {
                "name": "search_memories",
                "memory_ids": [str(value) for value in result.memory_ids],
                "mode": "temporal_sql" if result.direct else "full_text",
            }
        ]
        await queue.put(
            StreamEvent(
                event="tool_result",
                conversation_id=turn.conversation_id,
                message_id=turn.message_id,
                message=f"Retrieved {len(result.sources)} memory sources.",
            )
        )
        if result.direct:
            # A factual SQL rendering, never simulated model output or a fallback.
            text, turn.sources = (
                result.answer or "No supporting stored fact.",
                result.sources,
            )
        else:
            parent = self

            class CheckpointedProvider:
                async def stream(
                    self, messages: list[dict[str, str]]
                ) -> AsyncIterator[str]:
                    async for token in stream_graph(
                        parent.provider,
                        parent.saver,
                        f"{turn.user_id}:{turn.conversation_id}",
                        messages,
                    ):
                        yield token

            text, turn.sources = await grounded_answer(
                CheckpointedProvider(),
                turn.prompt[-1]["content"],
                result.sources,
                self.settings.llm_context_token_budget,
                turn.language,
            )
        for source in turn.sources:
            await queue.put(
                StreamEvent(
                    event="citation",
                    conversation_id=turn.conversation_id,
                    message_id=turn.message_id,
                    source=source.model_dump(mode="json"),
                )
            )
        for offset in range(0, len(text), 40):
            yield text[offset : offset + 40]

    @staticmethod
    def encode(event: StreamEvent) -> str:
        data = event.model_dump(mode="json", exclude_none=True)
        return f"event: {event.event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    async def web_tokens(
        self, turn: Turn, queue: asyncio.Queue[StreamEvent | None]
    ) -> AsyncIterator[str]:
        if not self.documents:
            raise ChatError(
                "SEARCH_UNAVAILABLE", "Search infrastructure is unavailable.", 503
            )
        query = turn.prompt[-1]["content"][8:].strip()
        if not 2 <= len(query) <= 500:
            raise ChatError(
                "SEARCH_QUERY_INVALID", "Use /search followed by 2-500 characters.", 422
            )
        await queue.put(
            StreamEvent(
                event="tool_start",
                conversation_id=turn.conversation_id,
                message_id=turn.message_id,
                message="Searching live web sources.",
            )
        )
        result = await asyncio.to_thread(
            SearchService(self.settings, self.documents.redis).search,
            turn.user_id,
            query,
        )
        sources = [
            SourceCitation(
                key=f"web:{i}",
                label=i,
                filename=s.title,
                excerpt=s.snippet,
                source_type="external_web",
                score=1,
                url=s.url,
                retrieved_at=s.retrieved_at,
                published_at=s.published_at,
            )
            for i, s in enumerate(result.sources, 1)
        ]
        turn.tool_calls = [
            {
                "name": "search_web",
                "result_count": len(sources),
                "cached": result.cached,
            }
        ]
        await queue.put(
            StreamEvent(
                event="tool_result",
                conversation_id=turn.conversation_id,
                message_id=turn.message_id,
                message=f"Retrieved {len(sources)} web sources with retrieval times.",
            )
        )
        if not sources:
            text = "No web search results found. No live facts established."
        else:
            parent = self

            class CheckpointedProvider:
                async def stream(
                    self, messages: list[dict[str, str]]
                ) -> AsyncIterator[str]:
                    async for token in stream_graph(
                        parent.provider,
                        parent.saver,
                        f"{turn.user_id}:{turn.conversation_id}",
                        messages,
                    ):
                        yield token

            text, turn.sources = await grounded_answer(
                CheckpointedProvider(),
                query,
                sources,
                self.settings.llm_context_token_budget,
                turn.language,
            )
        for source in turn.sources:
            await queue.put(
                StreamEvent(
                    event="citation",
                    conversation_id=turn.conversation_id,
                    message_id=turn.message_id,
                    source=source.model_dump(mode="json"),
                )
            )
        for offset in range(0, len(text), 40):
            yield text[offset : offset + 40]
