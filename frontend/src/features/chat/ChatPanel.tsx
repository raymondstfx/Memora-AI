import { useCallback, useEffect, useRef, useState } from "react";
import { MessageSquare, Plus, Send, Square } from "lucide-react";
import type { components } from "../../types/api.generated";
import { Button } from "../../components/ui/button";
import { api, readEvents, responseError, type ChatEvent } from "./stream";
import { CitationCards, type Citation } from "../knowledge/CitationCards";

type Conversation = components["schemas"]["ConversationOut"];
type Configuration = components["schemas"]["ChatConfiguration"];
type Message = Pick<
  components["schemas"]["MessageOut"],
  "id" | "role" | "content" | "status" | "error_code" | "citations_json"
>;
const selectedId = () =>
  new URLSearchParams(window.location.search).get("conversation");

export function ChatPanel() {
  const [documents, setDocuments] = useState<
    components["schemas"]["DocumentOut"][]
  >([]);
  const [documentIds, setDocumentIds] = useState<string[]>(() =>
    (new URLSearchParams(window.location.search).get("documents") || "")
      .split(",")
      .filter(Boolean),
  );
  const [embeddingReady, setEmbeddingReady] = useState(false);
  const [activity, setActivity] = useState("");
  const [config, setConfig] = useState<Configuration | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [active, setActive] = useState<string | null>(selectedId);
  const current = useRef(active);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [streaming, setStreaming] = useState(false);
  const pending = useRef<AbortController | null>(null);
  const responseId = useRef<string | null>(null);
  const end = useRef<HTMLDivElement>(null);
  const loadingSequence = useRef(0);

  const list = useCallback(
    async () => setConversations(await api<Conversation[]>("/conversations")),
    [],
  );
  const history = useCallback(async (id: string | null) => {
    const sequence = ++loadingSequence.current;
    setLoading(true);
    try {
      const rows = id
        ? await api<Message[]>(`/conversations/${id}/messages`)
        : [];
      if (loadingSequence.current === sequence && current.current === id)
        setMessages(rows);
    } catch (cause) {
      if (current.current === id)
        setError(
          cause instanceof Error ? cause.message : "Unable to load history.",
        );
    } finally {
      if (loadingSequence.current === sequence) setLoading(false);
    }
  }, []);

  const initialize = useCallback(async () => {
    setError("");
    try {
      await Promise.all([
        api<components["schemas"]["DocumentOut"][]>("/documents").then(
          setDocuments,
        ),
        api<components["schemas"]["DocumentConfiguration"]>(
          "/documents/config",
        ).then((value) => setEmbeddingReady(value.configured)),
        api<Configuration>("/chat/config").then(setConfig),
        list(),
        history(current.current),
      ]);
    } catch (cause) {
      setLoading(false);
      setError(cause instanceof Error ? cause.message : "Unable to load chat.");
    }
  }, [history, list]);

  useEffect(() => {
    void initialize();
    return () => {
      pending.current?.abort();
    };
  }, [initialize]);
  useEffect(() => {
    end.current?.scrollIntoView({ block: "nearest" });
  }, [messages]);

  const choose = async (id: string | null) => {
    if (streaming) return;
    current.current = id;
    setActive(id);
    setError("");
    setMessages([]);
    const url = new URL(window.location.href);
    if (id) url.searchParams.set("conversation", id);
    else url.searchParams.delete("conversation");
    window.history.replaceState(null, "", url);
    await history(id);
  };

  const send = async (retryId?: string) => {
    if (
      streaming ||
      !config?.configured ||
      (documentIds.length > 0 && !embeddingReady)
    )
      return;
    const text = draft.trim();
    if (!retryId && !text) return;
    const controller = new AbortController();
    pending.current = controller;
    responseId.current = null;
    setActivity("");
    setStreaming(true);
    setError("");
    if (!retryId) {
      setDraft("");
      setMessages((rows) => [
        ...rows,
        {
          id: crypto.randomUUID(),
          role: "user",
          content: text,
          status: "complete",
          error_code: null,
          citations_json: [],
        },
      ]);
    }
    const receive = (event: ChatEvent) => {
      if (event.event === "message_start") {
        responseId.current = event.message_id;
        current.current = event.conversation_id;
        setActive(event.conversation_id);
        const url = new URL(window.location.href);
        url.searchParams.set("conversation", event.conversation_id);
        window.history.replaceState(null, "", url);
        setMessages((rows) => [
          ...rows,
          {
            id: event.message_id,
            role: "assistant",
            content: "",
            status: "streaming",
            error_code: null,
            citations_json: [],
          },
        ]);
        void list().catch(() => undefined);
      } else if (event.event === "token") {
        setMessages((rows) =>
          rows.map((row) =>
            row.id === event.message_id
              ? { ...row, content: row.content + (event.text ?? "") }
              : row,
          ),
        );
      } else if (event.event === "citation" && event.source) {
        setMessages((rows) =>
          rows.map((row) =>
            row.id === event.message_id
              ? {
                  ...row,
                  citations_json: [...row.citations_json, event.source!],
                }
              : row,
          ),
        );
      } else if (
        event.event === "tool_start" ||
        event.event === "tool_result"
      ) {
        setActivity(event.message || "");
      } else if (event.event === "error") {
        setError(`${event.message} (${event.code}; ${event.request_id})`);
      }
    };
    try {
      const response = await fetch(
        retryId ? `/api/messages/${retryId}/retry` : "/api/chat/stream",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          signal: controller.signal,
          body: JSON.stringify(
            retryId
              ? { request_id: crypto.randomUUID() }
              : {
                  conversation_id: active,
                  message: text,
                  request_id: crypto.randomUUID(),
                  attachments: documentIds,
                },
          ),
        },
      );
      if (!response.ok) throw await responseError(response);
      await readEvents(response, receive);
    } catch (cause) {
      if (!(cause instanceof DOMException && cause.name === "AbortError")) {
        setError(
          cause instanceof Error ? cause.message : "Chat request failed.",
        );
        if (!responseId.current && !retryId) setDraft(text);
      }
    } finally {
      if (pending.current === controller) {
        pending.current = null;
        setStreaming(false);
        if (current.current) await history(current.current);
        else setMessages([]);
        await list().catch(() => undefined);
      }
    }
  };

  const stop = async () => {
    try {
      if (responseId.current)
        await api(`/messages/${responseId.current}/cancel`, { method: "POST" });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Stop request failed.");
    } finally {
      pending.current?.abort();
    }
  };

  const latest = messages.at(-1);
  const pendingHistory =
    !streaming && messages.some((row) => row.status === "streaming");
  useEffect(() => {
    if (!pendingHistory || !active) return;
    const timer = window.setInterval(() => void history(active), 2000);
    return () => window.clearInterval(timer);
  }, [pendingHistory, active, history]);
  const retryable =
    latest?.role === "assistant" &&
    ["failed", "incomplete", "interrupted", "cancelled"].includes(
      latest.status,
    );
  return (
    <section className="chat-workspace" aria-label="Chat workspace">
      <aside className="conversation-list" aria-label="Conversations">
        <Button onClick={() => void choose(null)} disabled={streaming}>
          <Plus size={15} /> New conversation
        </Button>
        {conversations.length === 0 && <p>No saved conversations yet.</p>}
        {conversations.map((row) => (
          <button
            key={row.id}
            disabled={streaming}
            className={
              row.id === active ? "conversation selected" : "conversation"
            }
            aria-pressed={row.id === active}
            onClick={() => void choose(row.id)}
          >
            <MessageSquare size={14} />
            <span>{row.title}</span>
          </button>
        ))}
      </aside>
      <div className="chat-main">
        <fieldset className="pdf-selector" disabled={streaming}>
          <legend>PDF evidence (optional, up to 5)</legend>
          {documents
            .filter((row) => row.status === "ready")
            .map((row) => (
              <label key={row.id}>
                <input
                  type="checkbox"
                  checked={documentIds.includes(row.id)}
                  onChange={(event) =>
                    setDocumentIds((ids) =>
                      event.target.checked
                        ? [...ids, row.id].slice(0, 5)
                        : ids.filter((id) => id !== row.id),
                    )
                  }
                />
                {row.filename}
              </label>
            ))}
          {!documents.some((row) => row.status === "ready") && (
            <small>No ready PDFs. Upload and index in Knowledge Base.</small>
          )}
          {documentIds.length > 0 && !embeddingReady && (
            <p>Configure backend Embedding credentials before querying PDFs.</p>
          )}
        </fieldset>
        {activity && (
          <p role="status" className="tool-activity">
            {activity}
          </p>
        )}
        {config && !config.configured && (
          <div className="configuration-notice" role="status">
            <strong>Chat configuration required / 请配置模型</strong>
            <p>{config.message}</p>
            <p>
              在后端项目根目录的 .env 填写 LLM_API_KEY、LLM_MODEL 和
              LLM_BASE_URL，然后重启 API。不会生成模拟回答。
            </p>
            <Button variant="outline" onClick={() => void initialize()}>
              Recheck configuration
            </Button>
          </div>
        )}
        {error && (
          <div role="alert" className="health-error">
            <p>{error}</p>
            <Button
              variant="outline"
              onClick={() => void initialize()}
              disabled={streaming}
            >
              Reload chat
            </Button>
          </div>
        )}
        <div
          className="chat-messages"
          aria-label="Message history"
          aria-busy={loading}
        >
          {loading && <p>Loading conversation…</p>}
          {!loading && messages.length === 0 && (
            <div className="chat-empty">
              <MessageSquare size={30} />
              <h2>Start a conversation</h2>
              <p>
                Ask a question. Conversations are saved locally in Postgres.
              </p>
              <small>
                Select ready PDFs below for grounded answers. Web tools remain
                unavailable.
              </small>
            </div>
          )}
          {messages.map((message) => (
            <article
              className={`chat-message ${message.role}`}
              key={message.id}
              aria-label={`${message.role} message`}
            >
              <strong>{message.role === "user" ? "You" : "Memora"}</strong>
              <div className="message-content">
                {message.content ||
                  (message.status === "streaming"
                    ? "Waiting for model…"
                    : "No answer was generated.")}
              </div>
              {message.status !== "complete" && (
                <small className="message-status">
                  {message.status}
                  {message.error_code ? ` · ${message.error_code}` : ""}
                </small>
              )}
              <CitationCards
                sources={message.citations_json as unknown as Citation[]}
              />
            </article>
          ))}
          <div ref={end} />
        </div>
        {retryable && !streaming && (
          <Button
            variant="outline"
            onClick={() => void send(latest.id)}
            disabled={!config?.configured}
          >
            Retry last response
          </Button>
        )}
        <form
          className="chat-composer"
          onSubmit={(event) => {
            event.preventDefault();
            void send();
          }}
        >
          <label htmlFor="chat-message">Message</label>
          <textarea
            id="chat-message"
            placeholder="Ask Memora…"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            maxLength={4000}
            disabled={streaming}
            rows={3}
          />
          <div>
            <small>
              {config?.configured
                ? `Model: ${config.model}. Messages are sent to your configured provider.`
                : "Add backend credentials to enable chat."}
            </small>
            {streaming ? (
              <Button
                type="button"
                variant="outline"
                onClick={() => void stop()}
              >
                <Square size={14} /> Stop response
              </Button>
            ) : (
              <Button
                type="submit"
                disabled={
                  !config?.configured ||
                  !draft.trim() ||
                  loading ||
                  (documentIds.length > 0 && !embeddingReady)
                }
              >
                <Send size={14} /> Send
              </Button>
            )}
          </div>
        </form>
      </div>
    </section>
  );
}
