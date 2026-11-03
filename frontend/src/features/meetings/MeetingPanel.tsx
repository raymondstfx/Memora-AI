import { useCallback, useEffect, useRef, useState } from "react";
import type { components } from "../../types/api.generated";
import { api } from "../chat/stream";
import { Button } from "../../components/ui/button";
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
          cause instanceof Error ? cause.message : "Unable to load meetings.",
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
        body: JSON.stringify({ date: date || null, timezone: zone || null }),
      });
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to retry.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="phase3-panel" aria-label="Meeting intelligence">
      <h2>Upload a meeting transcript</h2>
      <p>
        UTF-8 TXT, up to 64 KiB and the configured model context budget.
        Transcript text is sent to your configured LLM. No email is sent during
        analysis.
      </p>
      <label>
        Meeting date (optional ISO date)
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />
      </label>
      <label>
        Meeting timezone (IANA, optional)
        <input
          placeholder="Asia/Shanghai"
          value={zone}
          onChange={(e) => setZone(e.target.value)}
        />
      </label>
      <p>
        Metadata may be supplied in TXT headers: Title, Date, Timezone,
        Location. Relative deadlines require a meeting date and timezone.
      </p>
      <label>
        Upload meeting TXT
        <input
          type="file"
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
              if (date) form.append("date", date);
              if (zone) form.append("timezone", zone);
              const result = await api<components["schemas"]["MeetingUpload"]>(
                "/meetings/upload",
                { method: "POST", body: form },
              );
              setSelected(result.meeting_id);
              setNotice(
                result.duplicate
                  ? "Duplicate TXT: existing meeting and job reused."
                  : "Meeting queued for analysis.",
              );
              await refresh();
            } catch (cause) {
              setError(
                cause instanceof Error ? cause.message : "Upload failed.",
              );
            } finally {
              setBusy(false);
            }
          }}
        />
      </label>
      {busy && <p role="status">Working…</p>}
      {loading && <p role="status">Loading meetings…</p>}
      {notice && <p role="status">{notice}</p>}
      {error && (
        <div role="alert">
          {error}
          <Button
            onClick={() => {
              setError("");
              void refresh();
            }}
          >
            Retry loading
          </Button>
        </div>
      )}
      {!loading && !rows.length && (
        <p>No meetings yet. Upload a TXT transcript to begin.</p>
      )}
      <div className="meeting-list" aria-label="Saved meetings">
        {rows.map((m) => (
          <Button
            variant="outline"
            key={m.id}
            onClick={() => setSelected(m.id)}
          >
            {m.title} · {m.analysis_status}
          </Button>
        ))}
      </div>
      {analysis && (
        <article aria-label="Meeting analysis">
          <h2>{analysis.meeting.title}</h2>
          <p role="status">Analysis: {analysis.meeting.analysis_status}</p>
          {analysis.job && (
            <p>
              Processing stage: {analysis.job.stage} · {analysis.job.progress}%
            </p>
          )}
          <p>
            {analysis.meeting.occurred_at
              ? analysis.meeting.date_precision === "date"
                ? new Date(analysis.meeting.occurred_at).toLocaleDateString(
                    undefined,
                    { timeZone: analysis.meeting.timezone ?? "UTC" },
                  ) + " (start time unknown)"
                : new Date(analysis.meeting.occurred_at).toLocaleString(
                    undefined,
                    { timeZone: analysis.meeting.timezone ?? "UTC" },
                  )
              : "Date unknown"}{" "}
            · {analysis.meeting.timezone ?? "Timezone unknown"} ·{" "}
            {analysis.meeting.location ?? "Location unknown"}
          </p>
          {analysis.needs_review && (
            <p>
              Metadata needs review; unknown dates/owners are not fabricated.
            </p>
          )}
          {analysis.error_code && (
            <p role="alert">
              {analysis.error_code}: {analysis.error_message}
            </p>
          )}
          {analysis.meeting.analysis_status === "failed" && (
            <Button disabled={busy} onClick={() => void retry()}>
              Retry meeting analysis
            </Button>
          )}
          {analysis.analysis && (
            <>
              <h3>Summary</h3>
              <p>{analysis.analysis.summary}</p>
              <p>Topics: {(analysis.analysis.topics ?? []).join(", ")}</p>
              <h3>People</h3>
              <ul>
                {(analysis.analysis.people ?? []).map((p, i) => (
                  <li key={i}>
                    {p.name} · {p.role ?? "Role unknown"}
                    <blockquote>
                      Lines {p.evidence.line_start}–{p.evidence.line_end}:{" "}
                      {p.evidence.quote} ({p.evidence.kind})
                    </blockquote>
                  </li>
                ))}
              </ul>
              <h3>Decisions</h3>
              {(analysis.analysis.decisions ?? []).map((d, i) => (
                <div key={i}>
                  <p>{d.text}</p>
                  <blockquote>
                    Lines {d.evidence.line_start}–{d.evidence.line_end}:{" "}
                    {d.evidence.quote}
                  </blockquote>
                </div>
              ))}
            </>
          )}
          <h3>Risks</h3>
          {!analysis.risks.length && <p>No validated risks recorded.</p>}
          {analysis.risks.map((r) => (
            <section className="action-card" key={r.id}>
              <h4>
                {r.title} · {r.type} · {r.severity}
              </h4>
              <p>{r.rationale}</p>
              <p>Mitigation: {r.mitigation}</p>
              <blockquote>
                Lines {r.evidence_json.line_start}–{r.evidence_json.line_end}:{" "}
                {r.evidence_json.quote} ({r.evidence_json.kind})
              </blockquote>
              <small>
                Model confidence {r.confidence}; descriptive, not calibrated
                probability.
              </small>
            </section>
          ))}
          <h3>Proposed tasks</h3>
          {analysis.tasks.map((t) => (
            <TaskEditor
              key={`${t.id}:${t.updated_at}`}
              task={t}
              onSaved={() => void refresh()}
            />
          ))}
          <h3>Review email drafts</h3>
          {analysis.emails.map((e) => (
            <EmailEditor
              key={`${e.id}:${e.revision}`}
              email={e}
              onSaved={() => void refresh()}
            />
          ))}
          <details>
            <summary>Original transcript with source lines</summary>
            <ol className="transcript-lines">
              {lines.map((l) => (
                <li key={l.number} value={l.number}>
                  {l.text || " "}
                </li>
              ))}
            </ol>
          </details>
          <details>
            <summary>Audit history</summary>
            <ul>
              {events.map((e) => (
                <li key={e.id}>
                  {new Date(e.created_at).toLocaleString()} · {e.action} ·{" "}
                  {e.resource_id}
                </li>
              ))}
            </ul>
          </details>
        </article>
      )}
    </section>
  );
}
