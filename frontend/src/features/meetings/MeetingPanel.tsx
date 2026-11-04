import {
  formatNumber,
  errorMessage,
  t,
  getLanguage,
  formatDate,
} from "../../i18n";
import { useCallback, useEffect, useRef, useState } from "react";
import type { components } from "../../types/api.generated";
import { api } from "../chat/stream";
import { Button } from "../../components/ui/button";
import { Mic, FileText, CheckCircle2, Clock } from "lucide-react";
import { Metrics } from "../../components/ui/metrics";
import { EmailEditor, TaskEditor } from "./ActionsPanel";

type Meeting = components["schemas"]["MeetingOut"];
type Analysis = components["schemas"]["AnalysisOut"];
type Line = components["schemas"]["TranscriptLine"];
type Event = components["schemas"]["AuditOut"];

export function MeetingPanel() {
  const [rows, setRows] = useState<Meeting[]>([]);
  const [selected, setSelected] = useState("");
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [lines, setLines] = useState<Line[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [date, setDate] = useState("");
  const [zone, setZone] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const seq = useRef(0);
  const refresh = useCallback(async () => {
    const current = ++seq.current;
    try {
      const [meetings, detail, transcript, audit] = await Promise.all([
        api<Meeting[]>("/meetings"),
        selected
          ? api<Analysis>(`/meetings/${selected}/analysis`)
          : Promise.resolve(null),
        selected
          ? api<Line[]>(`/meetings/${selected}/transcript`)
          : Promise.resolve([]),
        selected
          ? api<Event[]>(`/meetings/${selected}/audit`)
          : Promise.resolve([]),
      ]);
      if (seq.current === current) {
        setRows(meetings);
        setAnalysis(detail);
        setLines(transcript);
        setEvents(audit);
      }
    } catch (cause) {
      if (seq.current === current)
        setError(
          cause instanceof Error
            ? cause.message
            : t("Unable to load meetings."),
        );
    } finally {
      if (seq.current === current) setLoading(false);
    }
  }, [selected]);
  useEffect(() => {
    setAnalysis(null);
    void refresh();
    const timer = setInterval(() => void refresh(), 2500);
    return () => {
      clearInterval(timer);
      ++seq.current;
    };
  }, [refresh]);
  const retry = async () => {
    setBusy(true);
    setError("");
    try {
      await api(`/meetings/${selected}/retry`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          date: date || null,
          timezone: zone || null,
          language: getLanguage(),
        }),
      });
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : t("Unable to retry."));
    } finally {
      setBusy(false);
    }
  };
  return (
    <section
      className="phase3-panel meetings-workspace"
      aria-label={t("Meeting intelligence")}
    >
      <Metrics
        items={[
          {
            label: "Saved meetings",
            value: loading ? null : rows.length,
            icon: Mic,
          },
          {
            label: "Ready analyses",
            value: loading
              ? null
              : rows.filter((m) => m.analysis_status === "ready").length,
            icon: CheckCircle2,
          },
          {
            label: "Needs attention",
            value: loading
              ? null
              : rows.filter((m) => m.analysis_status === "failed").length,
            icon: Clock,
          },
          {
            label: "Source format",
            value: "TXT",
            icon: FileText,
            hint: "UTF-8 TXT",
          },
        ]}
      />
      <div className="meeting-workbench">
        <aside className="meeting-index surface-card">
          <h2>{t("Upload a meeting transcript")}</h2>
          <p>
            {t(
              "UTF-8 TXT, up to 64 KiB and the configured model context budget. Transcript text is sent to your configured LLM. No email is sent during analysis.",
            )}
          </p>
          <label>
            {t("Meeting date (optional ISO date)")}
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </label>
          <label>
            {t("Meeting timezone (IANA, optional)")}
            <input
              placeholder="Asia/Shanghai"
              value={zone}
              onChange={(e) => setZone(e.target.value)}
            />
          </label>
          <p>
            {t(
              "Metadata may be supplied in TXT headers: Title, Date, Timezone, Location. Relative deadlines require a meeting date and timezone.",
            )}
          </p>
          <label>
            {t("Upload meeting TXT")}
            <span className="file-picker">
              <span aria-hidden="true" className="button button-outline">
                {t("Browse TXT")}
              </span>
              <input
                type="file"
                aria-label={t("Upload meeting TXT")}
                accept=".txt,text/plain"
                disabled={busy}
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  e.target.value = "";
                  if (!file) return;
                  setBusy(true);
                  setError("");
                  setNotice("");
                  try {
                    const form = new FormData();
                    form.append("file", file);
                    form.append("language", getLanguage());
                    if (date) form.append("date", date);
                    if (zone) form.append("timezone", zone);
                    const result = await api<
                      components["schemas"]["MeetingUpload"]
                    >("/meetings/upload", { method: "POST", body: form });
                    setSelected(result.meeting_id);
                    setNotice(
                      result.duplicate
                        ? t("Duplicate TXT: existing meeting and job reused.")
                        : t("Meeting queued for analysis."),
                    );
                    await refresh();
                  } catch (cause) {
                    setError(
                      cause instanceof Error
                        ? cause.message
                        : t("Upload failed."),
                    );
                  } finally {
                    setBusy(false);
                  }
                }}
              />
            </span>
          </label>
          {busy && <p role="status">{t("Working…")}</p>}
          {loading && <p role="status">{t("Loading meetings…")}</p>}
          {notice && <p role="status">{t(notice)}</p>}
          {error && (
            <div role="alert">
              {t(error)}
              <Button
                onClick={() => {
                  setError("");
                  void refresh();
                }}
              >
                {t("Retry loading")}
              </Button>
            </div>
          )}
          {!loading && !rows.length && (
            <p>{t("No meetings yet. Upload a TXT transcript to begin.")}</p>
          )}
          <div className="meeting-list" aria-label={t("Saved meetings")}>
            {rows.map((m) => (
              <Button
                variant="outline"
                aria-pressed={m.id === selected}
                key={m.id}
                onClick={() => setSelected(m.id)}
              >
                {m.title} · {t(m.analysis_status)}
              </Button>
            ))}
          </div>
        </aside>
        <div className="meeting-detail">
          {!selected && (
            <div className="selection-empty surface-card">
              <Mic size={30} />
              <h2>{t("Choose a meeting")}</h2>
              <p>
                {t(
                  "Select a saved meeting to review its summary, risks and original evidence.",
                )}
              </p>
            </div>
          )}
          {selected && !analysis && !error && (
            <p role="status">{t("Loading meeting analysis…")}</p>
          )}
          {analysis && (
            <article
              className="surface-card"
              aria-label={t("Meeting analysis")}
            >
              <h2>{analysis.meeting.title}</h2>
              <p role="status">
                {t("Analysis:")}
                {t(analysis.meeting.analysis_status)}
              </p>
              {analysis.job && (
                <p>
                  {t("Processing stage:")}
                  {t(analysis.job.stage)} ·{" "}
                  {formatNumber(analysis.job.progress)}%
                </p>
              )}
              <p>
                {analysis.meeting.occurred_at
                  ? formatDate(
                      analysis.meeting.occurred_at,
                      analysis.meeting.timezone ?? t("UTC"),
                      analysis.meeting.date_precision === "date",
                    ) +
                    (analysis.meeting.date_precision === "date"
                      ? " " + t("(start time unknown)")
                      : "")
                  : t("Date unknown")}{" "}
                · {analysis.meeting.timezone ?? t("Timezone unknown")} ·{" "}
                {analysis.meeting.location ?? t("Location unknown")}
              </p>
              {analysis.needs_review && (
                <p>
                  {t(
                    "Metadata needs review; unknown dates/owners are not fabricated.",
                  )}
                </p>
              )}
              {analysis.error_code && (
                <p role="alert">
                  {analysis.error_code}:{" "}
                  {errorMessage(
                    analysis.error_code,
                    analysis.error_message ?? "",
                  )}
                </p>
              )}
              {analysis.meeting.analysis_status === "failed" && (
                <Button disabled={busy} onClick={() => void retry()}>
                  {t("Retry meeting analysis")}
                </Button>
              )}
              {analysis.analysis && (
                <>
                  <h3>{t("Summary")}</h3>
                  <p>{analysis.analysis.summary}</p>
                  <p>
                    {t("Topics:")}
                    {(analysis.analysis.topics ?? []).join(", ")}
                  </p>
                  <h3>{t("People")}</h3>
                  <ul>
                    {(analysis.analysis.people ?? []).map((p, i) => (
                      <li key={i}>
                        {p.name} · {p.role ?? t("Role unknown")}
                        <blockquote>
                          {t("Lines")}
                          {p.evidence.line_start}–{p.evidence.line_end}:{" "}
                          {p.evidence.quote} ({t(p.evidence.kind)})
                        </blockquote>
                      </li>
                    ))}
                  </ul>
                  <h3>{t("Decisions")}</h3>
                  {(analysis.analysis.decisions ?? []).map((d, i) => (
                    <div key={i}>
                      <p>{d.text}</p>
                      <blockquote>
                        {t("Lines")}
                        {d.evidence.line_start}–{d.evidence.line_end}:{" "}
                        {d.evidence.quote}
                      </blockquote>
                    </div>
                  ))}
                </>
              )}
              <h3>{t("Risks")}</h3>
              {!analysis.risks.length && (
                <p>{t("No validated risks recorded.")}</p>
              )}
              {analysis.risks.map((r) => (
                <section className="action-card" key={r.id}>
                  <h4>
                    {r.title} · {t(r.type)} · {t(r.severity)}
                  </h4>
                  <p>{r.rationale}</p>
                  <p>
                    {t("Mitigation:")}
                    {r.mitigation}
                  </p>
                  <blockquote>
                    {t("Lines")}
                    {r.evidence_json.line_start}–{r.evidence_json.line_end}:{" "}
                    {r.evidence_json.quote} ({t(r.evidence_json.kind)})
                  </blockquote>
                  <small>
                    {t("Model confidence")}
                    {formatNumber(r.confidence)}
                    {t("; descriptive, not calibrated probability.")}
                  </small>
                </section>
              ))}
              <h3>{t("Proposed tasks")}</h3>
              {analysis.tasks.map((t) => (
                <TaskEditor
                  key={`${t.id}:${t.updated_at}`}
                  task={t}
                  onSaved={() => void refresh()}
                />
              ))}
              <h3>{t("Review email drafts")}</h3>
              {analysis.emails.map((e) => (
                <EmailEditor
                  key={`${e.id}:${e.revision}`}
                  email={e}
                  onSaved={() => void refresh()}
                />
              ))}
              <details>
                <summary>{t("Original transcript with source lines")}</summary>
                <ol className="transcript-lines">
                  {lines.map((l) => (
                    <li key={l.number} value={l.number}>
                      {l.text || " "}
                    </li>
                  ))}
                </ol>
              </details>
              <details>
                <summary>{t("Audit history")}</summary>
                <ul>
                  {events.map((e) => (
                    <li key={e.id}>
                      {formatDate(e.created_at)} · {e.action} · {e.resource_id}
                    </li>
                  ))}
                </ul>
              </details>
            </article>
          )}
        </div>
      </div>
    </section>
  );
}
