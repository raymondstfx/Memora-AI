import { useCallback, useEffect, useRef, useState } from "react";
import type { components } from "../../types/api.generated";
import { Button } from "../../components/ui/button";
import { api } from "../chat/stream";
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
      className="action-card"
      aria-label={`Memory ${row.subject_name} ${row.predicate}`}
    >
      <h3>
        {row.subject_name} · {row.predicate}
      </h3>
      <p role="status">
        {row.status} · {row.memory_type} · revision {row.revision}
      </p>
      <p>
        Valid from: {row.valid_from ?? "Unknown — needs review"}; valid until:{" "}
        {row.valid_to ?? "No recorded end"}
      </p>
      <p>
        Recorded: {row.observed_at} · {row.source_type}
      </p>
      <p>Stored value: {String(row.value_json.text)}</p>
      {row.correction_reason && (
        <p>
          User correction: {row.correction_reason}. The original quote is
          retained, not rewritten as proof of the correction.
        </p>
      )}
      {row.source && <CitationCards sources={[row.source]} />}
      <details>
        <summary>Correct or revoke this memory</summary>
        <p>
          Corrections create a new version. Revocation removes this fact from
          recall and retains its history; re-importing the source will not
          restore it.
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
                cause instanceof Error ? cause.message : "Correction failed.",
              );
            } finally {
              setBusy(false);
            }
          }}
        >
          <label>
            Corrected subject
            <select
              value={subject}
              disabled={locked || busy}
              onChange={(e) => setSubject(e.target.value)}
            >
              {entities.map((entity) => (
                <option key={entity.id} value={entity.id}>
                  {entity.canonical_name} ({entity.type})
                </option>
              ))}
            </select>
          </label>
          <label>
            Corrected value
            <input
              required
              maxLength={2000}
              value={value}
              disabled={locked || busy}
              onChange={(e) => setValue(e.target.value)}
            />
          </label>
          <label>
            Effective date/time (UTC)
            <input
              type="datetime-local"
              value={time}
              disabled={locked || busy}
              onChange={(e) => setTime(e.target.value)}
            />
          </label>
          <label>
            Correction reason
            <input
              required
              maxLength={1000}
              value={reason}
              disabled={locked || busy}
              onChange={(e) => setReason(e.target.value)}
            />
          </label>
          <Button type="submit" disabled={locked || busy}>
            Save corrected version
          </Button>
        </form>
        <Button
          variant="outline"
          disabled={locked || busy}
          onClick={async () => {
            if (
              !window.confirm(
                "Remove this memory from recall? Historical evidence is retained.",
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
                cause instanceof Error ? cause.message : "Revocation failed.",
              );
            } finally {
              setBusy(false);
            }
          }}
        >
          Revoke memory
        </Button>
      </details>
      {error && <p role="alert">{error}</p>}
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
        cause instanceof Error ? cause.message : "Identity update failed.",
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <section
      className="action-card"
      aria-label={`Entity ${entity.canonical_name}`}
    >
      <h3>
        {entity.canonical_name} · {entity.type}
      </h3>
      <p>Known names: {(entity.aliases ?? []).join(", ")}</p>
      <label>
        Confirmed alias
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
        Merge into the same identity
        <select
          value={target}
          onChange={(e) => {
            setTarget(e.target.value);
            setConfirmed(false);
          }}
        >
          <option value="">Choose canonical target</option>
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
        I confirm these names identify the same entity.
      </label>
      <Button
        disabled={busy || !alias.trim() || !confirmed}
        onClick={() => void save(false)}
      >
        Add confirmed alias
      </Button>
      <Button
        variant="outline"
        disabled={busy || !target || !confirmed}
        onClick={() => void save(true)}
      >
        Confirm identity merge
      </Button>
      {error && <p role="alert">{error}</p>}
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
          cause instanceof Error ? cause.message : "Unable to load memory.",
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
    <section className="phase3-panel" aria-label="Memory center">
      <p>
        Facts retain their meeting or chat sources. History, corrections and
        revoked records remain inspectable. Unknown or conflicting facts need
        review.
      </p>
      <p>
        Use <strong>Remember:</strong> in chat for explicit user assertions,
        such as “Remember: API owner is Alex”. Ordinary chat and assistant
        guesses are not automatically promoted to facts.
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
              `Imported ${result.processed} saved meetings; ${result.inserted} new memories. No model or Embedding calls.`,
            );
            await refresh();
          } catch (cause) {
            setError(cause instanceof Error ? cause.message : "Import failed.");
          } finally {
            setBusy(false);
          }
        }}
      >
        {cursor ? "Import next batch" : "Import saved meetings"}
      </Button>
      <Button variant="outline" onClick={() => void refresh()}>
        Refresh memory
      </Button>
      {notice && <p role="status">{notice}</p>}
      <div className="action-filters">
        <label>
          Memory status
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All history</option>
            {[
              "active",
              "superseded",
              "conflict",
              "needs_review",
              "corrected",
              "revoked",
            ].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </label>
        <label>
          Subject entity
          <select value={entity} onChange={(e) => setEntity(e.target.value)}>
            <option value="">All entities</option>
            {entities.map((e) => (
              <option key={e.id} value={e.id}>
                {e.canonical_name} ({e.type})
              </option>
            ))}
          </select>
        </label>
        <label>
          Memory type
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="">All types</option>
            <option>semantic</option>
            <option>episodic</option>
          </select>
        </label>
        <label>
          Valid at (UTC)
          <input
            type="datetime-local"
            value={at}
            onChange={(e) => setAt(e.target.value)}
          />
        </label>
      </div>
      {loading && <p role="status">Loading memories…</p>}
      {error && (
        <div role="alert">
          {error}
          <Button onClick={() => void refresh()}>Retry loading memory</Button>
        </div>
      )}
      {!loading && !rows.length && (
        <p>
          No matching memories. Import saved meetings or upload a dated meeting
          transcript.
        </p>
      )}
      <p>
        Showing up to 200 records. Filter by subject, status, type or effective
        time.
      </p>
      {rows.map((row) => (
        <MemoryCard
          key={`${row.id}:${row.revision}`}
          row={row}
          entities={entities}
          onSaved={() => void refresh()}
        />
      ))}
      <details>
        <summary>Entities and confirmed identity aliases</summary>
        <p>
          Only exact Unicode/case/space normalization is automatic. Titles,
          nicknames and similar names require your confirmation; a merge
          preserves original evidence.
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
