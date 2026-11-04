import { t, formatDate } from "../../i18n";
import { useCallback, useEffect, useRef, useState } from "react";
import type { components } from "../../types/api.generated";
import { Button } from "../../components/ui/button";
import { api } from "../chat/stream";
import { Brain, History, Link, AlertCircle } from "lucide-react";
import { Metrics } from "../../components/ui/metrics";
import { CitationCards } from "../knowledge/CitationCards";

type Memory = components["schemas"]["MemoryOut"];
type Entity = components["schemas"]["EntityOut"];

function MemoryCard({
  row,
  entities,
  onSaved,
}: {
  row: Memory;
  entities: Entity[];
  onSaved: () => void;
}) {
  const [value, setValue] = useState(String(row.value_json.text));
  const [reason, setReason] = useState("");
  const [time, setTime] = useState(row.valid_from?.slice(0, 16) ?? "");
  const [subject, setSubject] = useState(row.subject_entity_id);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const locked = row.lifecycle !== "recorded";
  return (
    <article
      className={`action-card memory-card memory-${row.status}`}
      aria-label={t("Memory {0} {1}", {
        0: row.subject_name,
        1: row.predicate,
      })}
    >
      <h3>
        {row.subject_name} · {t(row.predicate)}
      </h3>
      <p role="status">
        {t(row.status)} · {t(row.memory_type)}
        {t("· revision")}
        {row.revision}
      </p>
      <p>
        {t("Valid from:")}
        {row.valid_from
          ? formatDate(row.valid_from, "UTC")
          : t("Unknown — needs review")}
        {t("; valid until:")}{" "}
        {row.valid_to ? formatDate(row.valid_to, "UTC") : t("No recorded end")}
      </p>
      <p>
        {t("Recorded:")}
        {formatDate(row.observed_at, "UTC")} · {t(row.source_type)}
      </p>
      <p>
        {t("Stored value:")}
        {String(row.value_json.text)}
      </p>
      {row.correction_reason && (
        <p>
          {t("User correction:")}
          {row.correction_reason}
          {t(
            ". The original quote is retained, not rewritten as proof of the correction.",
          )}
        </p>
      )}
      {row.source && <CitationCards sources={[row.source]} />}
      <details>
        <summary>{t("Correct or revoke this memory")}</summary>
        <p>
          {t(
            "Corrections create a new version. Revocation removes this fact from recall and retains its history; re-importing the source will not restore it.",
          )}
        </p>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            setError("");
            try {
              await api(`/memories/${row.id}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  revision: row.revision,
                  value,
                  reason,
                  valid_from: time ? `${time}:00Z` : null,
                  subject_entity_id: subject,
                }),
              });
              onSaved();
            } catch (cause) {
              setError(
                cause instanceof Error
                  ? cause.message
                  : t("Correction failed."),
              );
            } finally {
              setBusy(false);
            }
          }}
        >
          <label>
            {t("Corrected subject")}
            <select
              value={subject}
              disabled={locked || busy}
              onChange={(e) => setSubject(e.target.value)}
            >
              {entities.map((entity) => (
                <option key={entity.id} value={entity.id}>
                  {entity.canonical_name} ({t(entity.type)})
                </option>
              ))}
            </select>
          </label>
          <label>
            {t("Corrected value")}
            <input
              required
              maxLength={2000}
              value={value}
              disabled={locked || busy}
              onChange={(e) => setValue(e.target.value)}
            />
          </label>
          <label>
            {t("Effective date/time (UTC)")}
            <input
              type="datetime-local"
              value={time}
              disabled={locked || busy}
              onChange={(e) => setTime(e.target.value)}
            />
          </label>
          <label>
            {t("Correction reason")}
            <input
              required
              maxLength={1000}
              value={reason}
              disabled={locked || busy}
              onChange={(e) => setReason(e.target.value)}
            />
          </label>
          <Button type="submit" disabled={locked || busy}>
            {t("Save corrected version")}
          </Button>
        </form>
        <Button
          variant="outline"
          disabled={locked || busy}
          onClick={async () => {
            if (
              !window.confirm(
                t(
                  "Remove this memory from recall? Historical evidence is retained.",
                ),
              )
            )
              return;
            setBusy(true);
            setError("");
            try {
              await api(`/memories/${row.id}?revision=${row.revision}`, {
                method: "DELETE",
              });
              onSaved();
            } catch (cause) {
              setError(
                cause instanceof Error
                  ? cause.message
                  : t("Revocation failed."),
              );
            } finally {
              setBusy(false);
            }
          }}
        >
          {t("Revoke memory")}
        </Button>
      </details>
      {error && <p role="alert">{t(error)}</p>}
    </article>
  );
}

function EntityEditor({
  entity,
  entities,
  onSaved,
}: {
  entity: Entity;
  entities: Entity[];
  onSaved: () => void;
}) {
  const [alias, setAlias] = useState("");
  const [target, setTarget] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const save = async (merge: boolean) => {
    setBusy(true);
    setError("");
    try {
      await api(`/entities/${entity.id}/${merge ? "merge" : "aliases"}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          revision: entity.revision,
          confirm_identity: true,
          ...(merge ? { target_id: target } : { alias }),
        }),
      });
      onSaved();
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : t("Identity update failed."),
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <section
      className="action-card"
      aria-label={t("Entity {0}", { 0: entity.canonical_name })}
    >
      <h3>
        {entity.canonical_name} · {t(entity.type)}
      </h3>
      <p>
        {t("Known names:")}
        {(entity.aliases ?? []).join(", ")}
      </p>
      <label>
        {t("Confirmed alias")}
        <input
          maxLength={180}
          value={alias}
          onChange={(e) => {
            setAlias(e.target.value);
            setConfirmed(false);
          }}
        />
      </label>
      <label>
        {t("Merge into the same identity")}
        <select
          value={target}
          onChange={(e) => {
            setTarget(e.target.value);
            setConfirmed(false);
          }}
        >
          <option value="">{t("Choose canonical target")}</option>
          {entities
            .filter((e) => e.id !== entity.id && e.type === entity.type)
            .map((e) => (
              <option key={e.id} value={e.id}>
                {e.canonical_name}
              </option>
            ))}
        </select>
      </label>
      <label className="approval-check">
        <input
          type="checkbox"
          checked={confirmed}
          onChange={(e) => setConfirmed(e.target.checked)}
        />
        {t("I confirm these names identify the same entity.")}
      </label>
      <Button
        disabled={busy || !alias.trim() || !confirmed}
        onClick={() => void save(false)}
      >
        {t("Add confirmed alias")}
      </Button>
      <Button
        variant="outline"
        disabled={busy || !target || !confirmed}
        onClick={() => void save(true)}
      >
        {t("Confirm identity merge")}
      </Button>
      {error && <p role="alert">{t(error)}</p>}
    </section>
  );
}

export function MemoryPanel() {
  const [rows, setRows] = useState<Memory[]>([]);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [status, setStatus] = useState("active");
  const [entity, setEntity] = useState("");
  const [kind, setKind] = useState("");
  const [at, setAt] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [cursor, setCursor] = useState<string | null>(null);
  const sequence = useRef(0);
  const refresh = useCallback(async () => {
    const current = ++sequence.current;
    setLoading(true);
    const query = new URLSearchParams();
    if (status) query.set("status", status);
    if (entity) query.set("entity_id", entity);
    if (kind) query.set("memory_type", kind);
    if (at) query.set("valid_at", `${at}:00Z`);
    try {
      const [memories, people] = await Promise.all([
        api<Memory[]>(`/memories?${query}`),
        api<Entity[]>("/entities"),
      ]);
      if (current === sequence.current) {
        setRows(memories);
        setEntities(people);
        setError("");
      }
    } catch (cause) {
      if (current === sequence.current)
        setError(
          cause instanceof Error ? cause.message : t("Unable to load memory."),
        );
    } finally {
      if (current === sequence.current) setLoading(false);
    }
  }, [status, entity, kind, at]);
  useEffect(() => {
    void refresh();
    return () => {
      ++sequence.current;
    };
  }, [refresh]);
  return (
    <section
      className="phase3-panel memory-workspace"
      aria-label={t("Memory center")}
    >
      <Metrics
        items={[
          {
            label: "Known entities",
            value: loading ? null : entities.length,
            icon: Brain,
          },
          {
            label: "Matching records",
            value: loading ? null : rows.length,
            icon: History,
          },
          {
            label: "Source-linked records",
            value: loading ? null : rows.filter((r) => r.source).length,
            icon: Link,
          },
          {
            label: "Needs review",
            value: loading
              ? null
              : rows.filter((r) =>
                  ["conflict", "needs_review"].includes(r.status),
                ).length,
            icon: AlertCircle,
          },
        ]}
      />
      <p>
        {t(
          "Facts retain their meeting or chat sources. History, corrections and revoked records remain inspectable. Unknown or conflicting facts need review.",
        )}
      </p>
      <p>
        {t("Use")}
        <strong>{t("Remember:")}</strong>
        {t(
          "in chat for explicit user assertions, such as “Remember: API owner is Alex”. Ordinary chat and assistant guesses are not automatically promoted to facts.",
        )}
      </p>
      <Button
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          setError("");
          try {
            const result = await api<components["schemas"]["ImportResult"]>(
              `/memories/import-meetings${cursor ? `?after=${cursor}` : ""}`,
              { method: "POST" },
            );
            setCursor(result.next_cursor ?? null);
            setNotice(
              t(
                "Imported {0} saved meetings; {1} new memories. No model or Embedding calls.",
                { 0: result.processed, 1: result.inserted },
              ),
            );
            await refresh();
          } catch (cause) {
            setError(
              cause instanceof Error ? cause.message : t("Import failed."),
            );
          } finally {
            setBusy(false);
          }
        }}
      >
        {cursor ? t("Import next batch") : t("Import saved meetings")}
      </Button>
      <Button variant="outline" onClick={() => void refresh()}>
        {t("Refresh memory")}
      </Button>
      {notice && <p role="status">{t(notice)}</p>}
      <div className="action-filters">
        <label>
          {t("Memory status")}
          <select
            aria-label={t("Memory status")}
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="">{t("All history")}</option>
            {[
              "active",
              "superseded",
              "conflict",
              "needs_review",
              "corrected",
              "revoked",
            ].map((v) => (
              <option key={v} value={v}>
                {t(v)}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("Subject entity")}
          <select
            aria-label={t("Subject entity")}
            value={entity}
            onChange={(e) => setEntity(e.target.value)}
          >
            <option value="">{t("All entities")}</option>
            {entities.map((e) => (
              <option key={e.id} value={e.id}>
                {e.canonical_name} ({t(e.type)})
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("Memory type")}
          <select
            aria-label={t("Memory type")}
            value={kind}
            onChange={(e) => setKind(e.target.value)}
          >
            <option value="">{t("All types")}</option>
            <option value="semantic">{t("semantic")}</option>
            <option value="episodic">{t("episodic")}</option>
          </select>
        </label>
        <label>
          {t("Valid at (UTC)")}
          <input
            type="datetime-local"
            value={at}
            onChange={(e) => setAt(e.target.value)}
          />
        </label>
      </div>
      {loading && <p role="status">{t("Loading memories…")}</p>}
      {error && (
        <div role="alert">
          {t(error)}
          <Button onClick={() => void refresh()}>
            {t("Retry loading memory")}
          </Button>
        </div>
      )}
      {!loading && !rows.length && (
        <p>
          {t(
            "No matching memories. Import saved meetings or upload a dated meeting transcript.",
          )}
        </p>
      )}
      <p>
        {t(
          "Showing up to 200 records. Filter by subject, status, type or effective time.",
        )}
      </p>
      <div className="memory-timeline">
        {rows.map((row) => (
          <MemoryCard
            key={`${row.id}:${row.revision}`}
            row={row}
            entities={entities}
            onSaved={() => void refresh()}
          />
        ))}
      </div>
      <details className="surface-card">
        <summary>{t("Entities and confirmed identity aliases")}</summary>
        <p>
          {t(
            "Only exact Unicode/case/space normalization is automatic. Titles, nicknames and similar names require your confirmation; a merge preserves original evidence.",
          )}
        </p>
        {entities.map((e) => (
          <EntityEditor
            key={`${e.id}:${e.revision}`}
            entity={e}
            entities={entities}
            onSaved={() => void refresh()}
          />
        ))}
      </details>
    </section>
  );
}
