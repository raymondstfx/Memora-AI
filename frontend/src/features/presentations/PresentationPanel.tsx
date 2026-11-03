import { useEffect, useRef, useState } from "react";
import { getDocument, GlobalWorkerOptions } from "pdfjs-dist";
import worker from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import type { components } from "../../types/api.generated";
import { api } from "../chat/stream";
import { Button } from "../../components/ui/button";
GlobalWorkerOptions.workerSrc = worker;
type Deck = components["schemas"]["DeckOut"];
type Search = components["schemas"]["WebSearchResult"];

function Preview({ id, count }: { id: string; count: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState("");
  const [rendered, setRendered] = useState(0);
  const [version, setVersion] = useState(0);
  useEffect(() => {
    let cancelled = false;
    setError("");
    setRendered(0);
    ref.current?.replaceChildren();
    const task = getDocument({ url: `/api/presentations/${id}/download.pdf` });
    const render = async () => {
      const pdf = await task.promise;
      if (pdf.numPages !== count) throw Error("Preview page count mismatch");
      const container = ref.current;
      if (!container || cancelled) return;
      container.replaceChildren();
      for (let page = 1; page <= count; page++) {
        if (cancelled) return;
        const doc = await pdf.getPage(page),
          viewport = doc.getViewport({ scale: 1 });
        const canvas = document.createElement("canvas");
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        canvas.style.width = "100%";
        canvas.style.height = "auto";
        canvas.setAttribute("role", "img");
        canvas.setAttribute("aria-label", `Slide ${page} of ${count}`);
        container.append(canvas);
        await doc.render({ canvas, viewport }).promise;
        if (!cancelled) setRendered(page);
      }
    };
    void render().catch((cause) => {
      if (!cancelled)
        setError(cause instanceof Error ? cause.message : "Preview failed");
    });
    return () => {
      cancelled = true;
      void task.destroy();
    };
  }, [id, count, version]);
  return (
    <section aria-label="Presentation preview">
      {!error && rendered < count && (
        <p role="status">
          Rendering preview {rendered}/{count} pages…
        </p>
      )}
      {error && (
        <>
          <p role="alert">Preview failed: {error}</p>
          <Button onClick={() => setVersion((value) => value + 1)}>
            Retry preview
          </Button>
        </>
      )}
      <div ref={ref} />
    </section>
  );
}

export function PresentationPanel() {
  const [decks, setDecks] = useState<Deck[]>([]),
    [selected, setSelected] = useState("");
  const [documents, setDocuments] = useState<
    components["schemas"]["DocumentOut"][]
  >([]);
  const [meetings, setMeetings] = useState<
    components["schemas"]["MeetingOut"][]
  >([]);
  const [docIds, setDocIds] = useState<string[]>([]),
    [meetingIds, setMeetingIds] = useState<string[]>([]);
  const [instruction, setInstruction] = useState(""),
    [language, setLanguage] = useState("en"),
    [count, setCount] = useState(6);
  const [memories, setMemories] = useState(true),
    [web, setWeb] = useState(false),
    [query, setQuery] = useState("");
  const [result, setResult] = useState<Search | null>(null),
    [config, setConfig] = useState("");
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [activity, setActivity] = useState("");
  const requestKey = useRef<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);
  const refresh = async () => setDecks(await api<Deck[]>("/presentations"));
  useEffect(() => {
    let alive = true;
    setLoading(true);
    void Promise.all([
      api<Deck[]>("/presentations"),
      api<components["schemas"]["DocumentOut"][]>("/documents"),
      api<components["schemas"]["MeetingOut"][]>("/meetings"),
      api<{ message: string }>("/search/config"),
    ])
      .then(([rows, docs, items, search]) => {
        if (alive) {
          setDecks(rows);
          setDocuments(docs);
          setMeetings(items);
          setConfig(search.message);
          setError("");
        }
      })
      .catch((cause) => {
        if (alive) setError(String(cause));
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [reload]);
  const pending = decks.some(
    (d) => d.status === "queued" || d.status === "running",
  );
  useEffect(() => {
    if (!pending) return;
    let alive = true;
    const timer = setInterval(() => {
      void api<Deck[]>("/presentations")
        .then((rows) => {
          if (alive) setDecks(rows);
        })
        .catch((cause) => {
          if (alive) setError(String(cause));
        });
    }, 2000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [pending]);
  const deck = decks.find((d) => d.id === selected);
  return (
    <section className="phase3-panel" aria-label="Presentations workspace">
      <h2>Search and create an editable presentation</h2>
      {loading && <p role="status">Loading presentation workspace…</p>}
      {!loading && !decks.length && (
        <p>No presentations yet. Select evidence and create your first deck.</p>
      )}
      <p>
        Selected private evidence is sent to your configured model. Web research
        is optional. No email is sent.
      </p>
      <p role="status">{config}</p>
      <label>
        Web search query
        <input
          maxLength={500}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </label>
      <Button
        disabled={busy || query.trim().length < 2}
        onClick={async () => {
          setBusy(true);
          setError("");
          setResult(null);
          setActivity("Searching live web sources…");
          try {
            const value = await api<Search>("/search", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ query }),
            });
            setResult(value);
            setActivity(
              value.cached
                ? "Cached search; original retrieval time retained."
                : "Search completed.",
            );
          } catch (cause) {
            setError(String(cause));
            setActivity("Search failed.");
          } finally {
            setBusy(false);
          }
        }}
      >
        Search web
      </Button>
      <p role="status">{activity}</p>
      {result && (
        <ul aria-label="Web search results">
          {result.sources.map((s) => (
            <li key={s.url}>
              <a href={s.url} target="_blank" rel="noreferrer">
                {s.title}
              </a>
              <p>{s.snippet}</p>
              <time dateTime={s.retrieved_at}>Retrieved {s.retrieved_at}</time>
              {s.published_at && <p>Published {s.published_at}</p>}
            </li>
          ))}
          {!result.sources.length && <li>No search results returned.</li>}
        </ul>
      )}
      <form
        onChange={() => {
          requestKey.current = null;
        }}
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          requestKey.current ??= crypto.randomUUID();
          try {
            const value = await api<Deck>("/presentations", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                request_key: requestKey.current,
                instruction,
                language,
                slide_count: count,
                document_ids: docIds,
                meeting_ids: meetingIds,
                use_memories: memories,
                web_query: web ? query : null,
              }),
            });
            setSelected(value.id);
            await refresh();
          } catch (cause) {
            setError(String(cause));
          } finally {
            setBusy(false);
          }
        }}
      >
        <label>
          Presentation instruction
          <textarea
            required
            minLength={5}
            maxLength={2000}
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
          />
        </label>
        <label>
          Language
          <select
            aria-label="Presentation language"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          >
            <option value="en">English</option>
            <option value="zh">中文</option>
          </select>
        </label>
        <label>
          Slide count
          <input
            type="number"
            required
            min={1}
            max={12}
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
          />
        </label>
        <fieldset>
          <legend>Ready PDF evidence (up to 5)</legend>
          {documents
            .filter((d) => d.kind === "PDF" && d.status === "ready")
            .map((d) => (
              <label key={d.id}>
                <input
                  type="checkbox"
                  checked={docIds.includes(d.id)}
                  disabled={!docIds.includes(d.id) && docIds.length >= 5}
                  onChange={(e) =>
                    setDocIds(
                      e.target.checked
                        ? [...docIds, d.id]
                        : docIds.filter((id) => id !== d.id),
                    )
                  }
                />
                {d.filename}
              </label>
            ))}
        </fieldset>
        <fieldset>
          <legend>Ready meeting evidence (up to 5)</legend>
          {meetings
            .filter((m) => m.analysis_status === "ready")
            .map((m) => (
              <label key={m.id}>
                <input
                  type="checkbox"
                  checked={meetingIds.includes(m.id)}
                  disabled={
                    !meetingIds.includes(m.id) && meetingIds.length >= 5
                  }
                  onChange={(e) =>
                    setMeetingIds(
                      e.target.checked
                        ? [...meetingIds, m.id]
                        : meetingIds.filter((id) => id !== m.id),
                    )
                  }
                />
                {m.title}
              </label>
            ))}
        </fieldset>
        <label>
          <input
            type="checkbox"
            checked={memories}
            onChange={(e) => setMemories(e.target.checked)}
          />
          Use owned memories
        </label>
        <label>
          <input
            type="checkbox"
            checked={web}
            onChange={(e) => setWeb(e.target.checked)}
          />
          Include optional web research using query above
        </label>
        <Button
          type="submit"
          disabled={busy || pending || (web && query.trim().length < 2)}
        >
          Generate presentation
        </Button>
      </form>
      {error && <p role="alert">{error}</p>}
      <Button variant="outline" onClick={() => setReload((value) => value + 1)}>
        Refresh presentations
      </Button>
      <nav aria-label="Saved presentations">
        {decks.map((d) => (
          <Button
            key={d.id}
            variant="outline"
            onClick={() => setSelected(d.id)}
          >
            {String(d.outline_json.presentation_title ?? "Presentation")} ·{" "}
            {d.status}
          </Button>
        ))}
      </nav>
      {deck && (
        <article aria-label="Presentation job">
          <p role="status">
            {deck.status} · {deck.stage} · {deck.progress}%
          </p>
          <progress
            aria-label="Generation progress"
            value={deck.progress}
            max={100}
          />
          {deck.status === "failed" && (
            <>
              <p role="alert">
                {deck.error_code}. Check configuration or source data; no
                partial output is available.
              </p>
              <Button
                disabled={busy || deck.attempts >= 3}
                onClick={async () => {
                  setBusy(true);
                  try {
                    await api(`/presentations/${deck.id}/retry`, {
                      method: "POST",
                    });
                    await refresh();
                  } catch (cause) {
                    setError(String(cause));
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Retry failed presentation
              </Button>
            </>
          )}
          {deck.status === "ready" && (
            <>
              <p>{deck.page_count} slides · editable PPTX and PDF preview</p>
              <a href={`/api/presentations/${deck.id}/download.pptx`}>
                Download editable PPTX
              </a>
              {" · "}
              <a
                href={`/api/presentations/${deck.id}/download.pdf`}
                target="_blank"
                rel="noreferrer"
              >
                Download PDF
              </a>
              <details>
                <summary>Structured outline and sources</summary>
                <pre style={{ whiteSpace: "pre-wrap" }}>
                  {JSON.stringify(
                    { outline: deck.outline_json, sources: deck.sources_json },
                    null,
                    2,
                  )}
                </pre>
              </details>
              <Preview id={deck.id} count={deck.page_count ?? 0} />
            </>
          )}
        </article>
      )}
    </section>
  );
}
