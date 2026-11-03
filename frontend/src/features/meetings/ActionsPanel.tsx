import { useCallback, useEffect, useRef, useState } from "react";
import type { components } from "../../types/api.generated";
import { api } from "../chat/stream";
import { Button } from "../../components/ui/button";

type Task = components["schemas"]["TaskOut"];
type Email = components["schemas"]["EmailOut"];

export function TaskEditor({
  task,
  onSaved,
}: {
  task: Task;
  onSaved: () => void;
}) {
  const [title, setTitle] = useState(task.title);
  const [owner, setOwner] = useState(task.owner_name ?? "");
  const [due, setDue] = useState(task.due_at?.slice(0, 16) ?? "");
  const [status, setStatus] = useState(task.status);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return (
    <form
      className="action-card"
      aria-label={`Task ${task.title}`}
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        setError("");
        try {
          await api(`/tasks/${task.id}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              title,
              owner_name: owner || null,
              due_at: due ? `${due}:00Z` : null,
              status,
            }),
          });
          onSaved();
        } catch (cause) {
          setError(
            cause instanceof Error ? cause.message : "Unable to save task.",
          );
        } finally {
          setBusy(false);
        }
      }}
    >
      <h3>{task.title}</h3>
      {task.needs_review && <p>Needs review: confirm owner and deadline.</p>}
      <label>
        Task title
        <input
          required
          value={title}
          maxLength={300}
          onChange={(e) => setTitle(e.target.value)}
        />
      </label>
      <label>
        Owner
        <input
          value={owner}
          maxLength={150}
          onChange={(e) => setOwner(e.target.value)}
        />
      </label>
      <label>
        Due date/time (UTC)
        <input
          type="datetime-local"
          value={due}
          onChange={(e) => setDue(e.target.value)}
        />
      </label>
      <label>
        Task status
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          {["proposed", "open", "in_progress", "done", "cancelled"].map((v) => (
            <option key={v}>{v}</option>
          ))}
        </select>
      </label>
      <blockquote>
        Lines {task.evidence_json.line_start}–{task.evidence_json.line_end}:{" "}
        {task.evidence_json.quote}
      </blockquote>
      {error && <p role="alert">{error}</p>}
      <Button disabled={busy} type="submit">
        {busy ? "Saving…" : "Save task"}
      </Button>
    </form>
  );
}

export function EmailEditor({
  email,
  onSaved,
}: {
  email: Email;
  onSaved: () => void;
}) {
  const [recipients, setRecipients] = useState(
    email.recipients_json.join(", "),
  );
  const [subject, setSubject] = useState(email.subject);
  const [body, setBody] = useState(email.body);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const approvalKey = useRef(crypto.randomUUID());
  const locked =
    ["queued", "sending", "sent"].includes(email.send_status) ||
    email.error_code === "SMTP_DELIVERY_UNCERTAIN";
  const dirty =
    subject !== email.subject ||
    body !== email.body ||
    recipients !== email.recipients_json.join(", ");
  const run = async (approve: boolean) => {
    setBusy(true);
    setError("");
    if (
      approve &&
      email.send_status === "failed" &&
      email.error_code !== "SMTP_DELIVERY_UNCERTAIN"
    ) {
      // A fresh explicit approval may retry only a known non-delivery.
      approvalKey.current = crypto.randomUUID();
    }
    try {
      await api(`/emails/${email.id}${approve ? "/approve-send" : ""}`, {
        method: approve ? "POST" : "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          approve
            ? {
                revision: email.revision,
                idempotency_key: approvalKey.current,
                confirm_send: true,
              }
            : {
                revision: email.revision,
                recipients: recipients
                  .split(",")
                  .map((v) => v.trim())
                  .filter(Boolean),
                subject,
                body,
              },
        ),
      });
      setConfirmed(false);
      onSaved();
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Unable to update email.",
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="action-card" aria-label={`Email ${email.subject}`}>
      <h3>Email draft · revision {email.revision}</h3>
      <p role="status">
        {email.approval_status} · {email.send_status}
        {email.error_code ? ` · ${email.error_code}` : ""}
      </p>
      {email.sent_at && (
        <p>
          SMTP accepted: {new Date(email.sent_at).toLocaleString()} ·{" "}
          {email.provider_message_id}
        </p>
      )}
      {email.error_code === "SMTP_DELIVERY_UNCERTAIN" && (
        <p role="alert">
          Delivery is uncertain. Check the mailbox before taking further action.
          Automatic resend is blocked.
        </p>
      )}
      <label>
        Recipients (comma separated)
        <input
          value={recipients}
          disabled={locked || busy}
          onChange={(e) => {
            setRecipients(e.target.value);
            setConfirmed(false);
          }}
        />
      </label>
      <label>
        Subject
        <input
          value={subject}
          maxLength={300}
          disabled={locked || busy}
          onChange={(e) => {
            setSubject(e.target.value);
            setConfirmed(false);
          }}
        />
      </label>
      <label>
        Email body
        <textarea
          rows={10}
          value={body}
          maxLength={12000}
          disabled={locked || busy}
          onChange={(e) => {
            setBody(e.target.value);
            setConfirmed(false);
          }}
        />
      </label>
      <p>
        Recipients must be explicitly chosen from the configured allowlist.
        Names never become inferred email addresses.
      </p>
      <Button
        variant="outline"
        disabled={locked || busy || !dirty}
        onClick={() => void run(false)}
      >
        Save draft
      </Button>
      <label className="approval-check">
        <input
          type="checkbox"
          checked={confirmed}
          disabled={locked || busy || dirty}
          onChange={(e) => setConfirmed(e.target.checked)}
        />
        I approve sending this saved revision to the recipients shown above.
      </label>
      <Button
        disabled={
          locked || busy || dirty || !confirmed || !email.recipients_json.length
        }
        onClick={() => void run(true)}
      >
        {busy ? "Working…" : "Approve & send email"}
      </Button>
      {dirty && <p>Save your changes before approving.</p>}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}

export function ActionsPanel() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [emails, setEmails] = useState<Email[]>([]);
  const [status, setStatus] = useState("");
  const [owner, setOwner] = useState("");
  const [due, setDue] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const seq = useRef(0);
  const refresh = useCallback(async () => {
    const current = ++seq.current;
    const query = new URLSearchParams();
    if (status) query.set("status", status);
    if (owner) query.set("owner_name", owner);
    if (due) query.set("due_before", `${due}T23:59:59Z`);
    try {
      const [t, e] = await Promise.all([
        api<Task[]>(`/tasks?${query}`),
        api<Email[]>("/emails"),
      ]);
      if (seq.current === current) {
        setTasks(t);
        setEmails(e);
        setError("");
      }
    } catch (cause) {
      if (seq.current === current)
        setError(
          cause instanceof Error ? cause.message : "Unable to load actions.",
        );
    } finally {
      if (seq.current === current) setLoading(false);
    }
  }, [status, owner, due]);
  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 3000);
    return () => {
      clearInterval(timer);
      ++seq.current;
    };
  }, [refresh]);
  return (
    <section className="phase3-panel" aria-label="Tasks and approved actions">
      <p>Tasks are proposals until reviewed. Saving a draft never sends it.</p>
      <div className="action-filters">
        <label>
          Filter status
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All</option>
            {["proposed", "open", "in_progress", "done", "cancelled"].map(
              (v) => (
                <option key={v}>{v}</option>
              ),
            )}
          </select>
        </label>
        <label>
          Filter owner
          <input value={owner} onChange={(e) => setOwner(e.target.value)} />
        </label>
        <label>
          Due before (UTC)
          <input
            type="date"
            value={due}
            onChange={(e) => setDue(e.target.value)}
          />
        </label>
      </div>
      {loading && <p role="status">Loading actions…</p>}
      {error && (
        <div role="alert">
          {error}
          <Button onClick={() => void refresh()}>Retry loading</Button>
        </div>
      )}
      {!loading && !tasks.length && <p>No matching tasks.</p>}
      {tasks.map((t) => (
        <TaskEditor
          key={`${t.id}:${t.updated_at}`}
          task={t}
          onSaved={() => void refresh()}
        />
      ))}
      <h2>Email drafts and delivery</h2>
      {!loading && !emails.length && <p>No email drafts yet.</p>}
      {emails.map((e) => (
        <EmailEditor
          key={`${e.id}:${e.revision}`}
          email={e}
          onSaved={() => void refresh()}
        />
      ))}
    </section>
  );
}
