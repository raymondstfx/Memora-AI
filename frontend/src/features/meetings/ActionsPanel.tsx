import { t, formatDate } from "../../i18n";
import { useCallback, useEffect, useRef, useState } from "react";
import type { components } from "../../types/api.generated";
import { api } from "../chat/stream";
import {
  CheckSquare,
  Mail,
  CheckCircle2,
  AlertCircle,
  ShieldCheck,
} from "lucide-react";
import { Metrics } from "../../components/ui/metrics";
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
      aria-label={t("Task {0}", { 0: task.title })}
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
            cause instanceof Error ? cause.message : t("Unable to save task."),
          );
        } finally {
          setBusy(false);
        }
      }}
    >
      <h3>{task.title}</h3>
      {task.needs_review && (
        <p>{t("Needs review: confirm owner and deadline.")}</p>
      )}
      <label>
        {t("Task title")}
        <input
          required
          value={title}
          maxLength={300}
          onChange={(e) => setTitle(e.target.value)}
        />
      </label>
      <label>
        {t("Owner")}
        <input
          value={owner}
          maxLength={150}
          onChange={(e) => setOwner(e.target.value)}
        />
      </label>
      <label>
        {t("Due date/time (UTC)")}
        <input
          type="datetime-local"
          value={due}
          onChange={(e) => setDue(e.target.value)}
        />
      </label>
      <label>
        {t("Task status")}
        <select
          aria-label={t("Task status")}
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          {["proposed", "open", "in_progress", "done", "cancelled"].map((v) => (
            <option key={v} value={v}>
              {t(v)}
            </option>
          ))}
        </select>
      </label>
      <blockquote>
        {t("Lines")}
        {task.evidence_json.line_start}–{task.evidence_json.line_end}:{" "}
        {task.evidence_json.quote}
      </blockquote>
      {error && <p role="alert">{t(error)}</p>}
      <Button disabled={busy} type="submit">
        {busy ? t("Saving…") : t("Save task")}
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
        cause instanceof Error ? cause.message : t("Unable to update email."),
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <section
      className="action-card email-card"
      aria-label={t("Email {0}", { 0: email.subject })}
    >
      <h3>
        {t("Email draft · revision")}
        {email.revision}
      </h3>
      <p role="status">
        {t(email.approval_status)} · {t(email.send_status)}
        {email.error_code ? ` · ${email.error_code}` : ""}
      </p>
      {email.sent_at && (
        <p>
          {t("SMTP accepted:")}
          {formatDate(email.sent_at)} · {email.provider_message_id}
        </p>
      )}
      {email.error_code === "SMTP_DELIVERY_UNCERTAIN" && (
        <p role="alert">
          {t(
            "Delivery is uncertain. Check the mailbox before taking further action. Automatic resend is blocked.",
          )}
        </p>
      )}
      <label>
        {t("Recipients (comma separated)")}
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
        {t("Subject")}
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
        {t("Email body")}
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
        {t(
          "Recipients must be explicitly chosen from the configured allowlist. Names never become inferred email addresses.",
        )}
      </p>
      <Button
        variant="outline"
        disabled={locked || busy || !dirty}
        onClick={() => void run(false)}
      >
        {t("Save draft")}
      </Button>
      <label className="approval-check">
        <input
          type="checkbox"
          checked={confirmed}
          disabled={locked || busy || dirty}
          onChange={(e) => setConfirmed(e.target.checked)}
        />
        {t(
          "I approve sending this saved revision to the recipients shown above.",
        )}
      </label>
      <Button
        disabled={
          locked || busy || dirty || !confirmed || !email.recipients_json.length
        }
        onClick={() => void run(true)}
      >
        {busy ? t("Working…") : t("Approve & send email")}
      </Button>
      {dirty && <p>{t("Save your changes before approving.")}</p>}
      {error && <p role="alert">{t(error)}</p>}
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
          cause instanceof Error ? cause.message : t("Unable to load actions."),
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
    <section
      className="phase3-panel actions-workspace"
      aria-label={t("Tasks and approved actions")}
    >
      <div className="info-banner">
        <ShieldCheck size={20} />
        <p>{t("Human approval is required. Saving a draft never sends it.")}</p>
      </div>
      <Metrics
        items={[
          {
            label: "Matching tasks",
            value: loading ? null : tasks.length,
            icon: CheckSquare,
          },
          {
            label: "Email drafts",
            value: loading
              ? null
              : emails.filter((e) => e.send_status !== "sent").length,
            icon: Mail,
          },
          {
            label: "SMTP accepted",
            value: loading
              ? null
              : emails.filter((e) => e.send_status === "sent").length,
            icon: CheckCircle2,
          },
          {
            label: "Delivery needs attention",
            value: loading
              ? null
              : emails.filter(
                  (e) =>
                    e.send_status === "failed" ||
                    e.error_code === "SMTP_DELIVERY_UNCERTAIN",
                ).length,
            icon: AlertCircle,
          },
        ]}
      />
      <p>
        {t(
          "Tasks are proposals until reviewed. Saving a draft never sends it.",
        )}
      </p>
      <div className="action-filters">
        <label>
          {t("Filter status")}
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">{t("All")}</option>
            {["proposed", "open", "in_progress", "done", "cancelled"].map(
              (v) => (
                <option key={v} value={v}>
                  {t(v)}
                </option>
              ),
            )}
          </select>
        </label>
        <label>
          {t("Filter owner")}
          <input value={owner} onChange={(e) => setOwner(e.target.value)} />
        </label>
        <label>
          {t("Due before (UTC)")}
          <input
            type="date"
            value={due}
            onChange={(e) => setDue(e.target.value)}
          />
        </label>
      </div>
      {loading && <p role="status">{t("Loading actions…")}</p>}
      {error && (
        <div role="alert">
          {t(error)}
          <Button onClick={() => void refresh()}>{t("Retry loading")}</Button>
        </div>
      )}
      <div className="actions-columns">
        <div>
          <h2>{t("Tasks & Actions")}</h2>
          {!loading && !tasks.length && <p>{t("No matching tasks.")}</p>}
          {tasks.map((t) => (
            <TaskEditor
              key={`${t.id}:${t.updated_at}`}
              task={t}
              onSaved={() => void refresh()}
            />
          ))}
        </div>
        <div>
          <h2>{t("Email drafts and delivery")}</h2>
          {!loading && !emails.length && <p>{t("No email drafts yet.")}</p>}
          {emails.map((e) => (
            <EmailEditor
              key={`${e.id}:${e.revision}`}
              email={e}
              onSaved={() => void refresh()}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
