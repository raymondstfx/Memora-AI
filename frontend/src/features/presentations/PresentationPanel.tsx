import { errorMessage, t, formatDate, useLanguage } from "../../i18n";
import { useEffect, useRef, useState } from "react";
import { getDocument, GlobalWorkerOptions } from "pdfjs-dist";
import worker from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import type { components } from "../../types/api.generated";
import { api } from "../chat/stream";
import {
  FileSliders,
  Download,
  Globe,
  ArrowDown,
  CheckCircle2,
} from "lucide-react";
import { Button } from "../../components/ui/button";
GlobalWorkerOptions.workerSrc = worker;
type Deck = components["schemas"]["DeckOut"];
type Search = components["schemas"]["WebSearchResult"];

function Preview({
  id,
  count,
  outline,
}: {
  id: string;
  count: number;
  outline: Deck["outline_json"];
}) {
  const [activePage, setActivePage] = useState(1);
  const slides = Array.isArray(outline.slides) ? outline.slides : [];
  const uiLanguage = useLanguage();
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
      if (pdf.numPages !== count) throw Error(t("Preview page count mismatch"));
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
        canvas.setAttribute(
          "aria-label",
          t("Slide {0} of {1}", { 0: page, 1: count }),
        );
        container.append(canvas);
        await doc.render({ canvas, viewport }).promise;
        if (!cancelled) setRendered(page);
      }
    };
    void render().catch((cause) => {
      if (!cancelled)
        setError(cause instanceof Error ? cause.message : t("Preview failed"));
    });
    return () => {
      cancelled = true;
      void task.destroy();
    };
  }, [id, count, version]);
  useEffect(() => {
    ref.current
      ?.querySelectorAll("canvas")
      .forEach((canvas, i) =>
        canvas.setAttribute(
          "aria-label",
          t("Slide {0} of {1}", { 0: i + 1, 1: count }),
        ),
      );
  }, [uiLanguage, rendered, count]);
  return (
    <section className="deck-preview" aria-label={t("Presentation preview")}>
      <aside className="slide-index">
        <h3>
          <FileSliders size={17} />
          {t("Slide outline")}
        </h3>
        {Array.from({ length: count }, (_, i) => {
          const slide = slides[i] as
            { title?: string; bullets?: string[] } | undefined;
          return (
            <button
              className={`slide-thumbnail ${activePage === i + 1 ? "selected" : ""}`}
              aria-pressed={activePage === i + 1}
              key={i}
              onClick={() => {
                setActivePage(i + 1);
                ref.current?.children[i]?.scrollIntoView({
                  behavior: "smooth",
                  block: "nearest",
                });
              }}
            >
              <span className="thumbnail-number">
                {String(i + 1).padStart(2, "0")} / {count}
              </span>
              <strong>
                {slide?.title ?? t("Slide {0} of {1}", { 0: i + 1, 1: count })}
              </strong>
              <small>{slide?.bullets?.[0] ?? ""}</small>
              <span className="card-link">
                {t("View slide")}
                <ArrowDown size={13} />
              </span>
            </button>
          );
        })}
      </aside>
      <div className="preview-viewport">
        <div className="preview-toolbar">
          <span>{t("PDF preview")}</span>
          <span>{t("{0} pages", { 0: count })}</span>
        </div>
        {!error && rendered < count && (
          <p role="status">
            {t("Rendering preview")}
            {rendered}/{count}
            {t("pages…")}
          </p>
        )}
        {error && (
          <>
            <p role="alert">
              {t("Preview failed:")}
              {t(error)}
            </p>
            <Button onClick={() => setVersion((value) => value + 1)}>
              {t("Retry preview")}
            </Button>
          </>
        )}
        <div className="pdf-pages" ref={ref} />
      </div>
    </section>
  );
}

export function PresentationPanel() {
  const uiLanguage = useLanguage();
  const [configOpen, setConfigOpen] = useState(true);
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
    [language, setLanguage] = useState(""),
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
  useEffect(() => {
    requestKey.current = null;
  }, [uiLanguage]);
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
    <section
      className="phase3-panel presentation-workspace"
      aria-label={t("Presentations workspace")}
    >
      <details
        className="presentation-config surface-card"
        open={configOpen}
        onToggle={(e) => setConfigOpen(e.currentTarget.open)}
      >
        <summary>
          <FileSliders size={19} />
          {t("Search and create an editable presentation")}
        </summary>
        {loading && <p role="status">{t("Loading presentation workspace…")}</p>}
        {!loading && !decks.length && (
          <p>
            {t(
              "No presentations yet. Select evidence and create your first deck.",
            )}
          </p>
        )}
        <p>
          {t(
            "Selected private evidence is sent to your configured model. Web research is optional. No email is sent.",
          )}
        </p>
        <p role="status">{t(config)}</p>
        <div className="web-research">
          <h3>
            <Globe size={17} />
            {t("Web research")}
          </h3>
          <label>
            {t("Web search query")}
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
              setActivity(t("Searching live web sources…"));
              try {
                const value = await api<Search>("/search", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ query }),
                });
                setResult(value);
                setActivity(
                  value.cached
                    ? t("Cached search; original retrieval time retained.")
                    : t("Search completed."),
                );
              } catch (cause) {
                setError(String(cause));
                setActivity(t("Search failed."));
              } finally {
                setBusy(false);
              }
            }}
          >
            {t("Search web")}
          </Button>
          <p role="status">{t(activity)}</p>
          {result && (
            <ul aria-label={t("Web search results")}>
              {result.sources.map((s) => (
                <li key={s.url}>
                  <a href={s.url} target="_blank" rel="noreferrer">
                    {s.title}
                  </a>
                  <p>{s.snippet}</p>
                  <time dateTime={s.retrieved_at}>
                    {t("Retrieved")}
                    {formatDate(s.retrieved_at, "UTC")}
                  </time>
                  {s.published_at && (
                    <p>
                      {t("Published")}
                      {s.published_at}
                    </p>
                  )}
                </li>
              ))}
              {!result.sources.length && (
                <li>{t("No search results returned.")}</li>
              )}
            </ul>
          )}
        </div>
        <form
          className="presentation-form"
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
                  language: language || uiLanguage,
                  slide_count: count,
                  document_ids: docIds,
                  meeting_ids: meetingIds,
                  use_memories: memories,
                  web_query: web ? query : null,
                }),
              });
              setSelected(value.id);
              setConfigOpen(false);
              await refresh();
            } catch (cause) {
              setError(String(cause));
            } finally {
              setBusy(false);
            }
          }}
        >
          <label>
            {t("Presentation instruction")}
            <textarea
              required
              minLength={5}
              maxLength={2000}
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
            />
          </label>
          <label>
            {t("Language")}
            <select
              aria-label={t("Presentation language")}
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
            >
              <option value="">{t("Follow interface language")}</option>
              <option value="en">{t("English")}</option>
              <option value="zh">中文</option>
            </select>
          </label>
          <label>
            {t("Slide count")}
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
            <legend>{t("Ready PDF evidence (up to 5)")}</legend>
            {!documents.some(
              (d) => d.kind === "PDF" && d.status === "ready",
            ) && (
              <small>
                {t("No ready PDFs. Upload and index in Knowledge Base.")}
              </small>
            )}
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
            <legend>{t("Ready meeting evidence (up to 5)")}</legend>
            {!meetings.some((m) => m.analysis_status === "ready") && (
              <small>
                {t("No ready meetings. Upload a transcript in Meetings.")}
              </small>
            )}
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
            {t("Use owned memories")}
          </label>
          <label>
            <input
              type="checkbox"
              checked={web}
              onChange={(e) => setWeb(e.target.checked)}
            />
            {t("Include optional web research using query above")}
          </label>
          <Button
            type="submit"
            disabled={busy || pending || (web && query.trim().length < 2)}
          >
            {t("Generate presentation")}
          </Button>
        </form>
        {error && <p role="alert">{t(error)}</p>}
      </details>
      <div className="saved-deck-toolbar">
        <label>
          {t("Saved presentations")}
          <select
            value={selected}
            onChange={(e) => {
              setSelected(e.target.value);
              if (e.target.value) setConfigOpen(false);
            }}
          >
            <option value="">{t("Choose a presentation")}</option>
            {decks.map((d) => (
              <option key={d.id} value={d.id}>
                {String(d.outline_json.presentation_title ?? t("Presentation"))}{" "}
                · {t(d.status)} · {d.id.slice(0, 8)}
              </option>
            ))}
          </select>
        </label>
        <Button
          variant="outline"
          onClick={() => setReload((value) => value + 1)}
        >
          {t("Refresh presentations")}
        </Button>
      </div>
      {deck && (
        <article
          className="presentation-job surface-card"
          aria-label={t("Presentation job")}
        >
          <h2>
            {String(deck.outline_json.presentation_title ?? t("Presentation"))}
          </h2>
          <div className="pipeline">
            <span className={deck.status === "ready" ? "complete" : ""}>
              <CheckCircle2 size={15} />
              {t("Evidence")}
            </span>
            <span aria-hidden="true">→</span>
            <span>{t("Outline")}</span>
            <span aria-hidden="true">→</span>
            <span>{t("Validation")}</span>
            <span aria-hidden="true">→</span>
            <span>{t("PPTX + PDF")}</span>
          </div>
          <p role="status">
            {t(deck.status)} · {t(deck.stage)} · {deck.progress}%
          </p>
          <progress
            aria-label={t("Generation progress")}
            value={deck.progress}
            max={100}
          />
          {deck.status === "failed" && (
            <>
              <p role="alert">
                {deck.error_code}:{" "}
                {errorMessage(deck.error_code, deck.error_message ?? "")}
                {t(
                  ". Check configuration or source data; no partial output is available.",
                )}
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
                {t("Retry failed presentation")}
              </Button>
            </>
          )}
          {deck.status === "ready" && (
            <>
              <p>
                {deck.page_count}
                {t("slides · editable PPTX and PDF preview")}
              </p>
              <div className="download-actions">
                <a
                  className="button button-primary"
                  href={`/api/presentations/${deck.id}/download.pptx`}
                >
                  <Download size={16} />
                  {t("Download editable PPTX")}
                </a>
                {" · "}
                <a
                  className="button button-outline"
                  href={`/api/presentations/${deck.id}/download.pdf`}
                  target="_blank"
                  rel="noreferrer"
                >
                  {t("Download PDF")}
                </a>
              </div>
              <details>
                <summary>{t("Structured outline and sources")}</summary>
                <pre style={{ whiteSpace: "pre-wrap" }}>
                  {JSON.stringify(
                    { outline: deck.outline_json, sources: deck.sources_json },
                    null,
                    2,
                  )}
                </pre>
              </details>
              <Preview
                key={deck.id}
                id={deck.id}
                count={deck.page_count ?? 0}
                outline={deck.outline_json}
              />
            </>
          )}
        </article>
      )}
    </section>
  );
}
