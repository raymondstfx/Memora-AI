import { useCallback, useEffect, useState } from "react";
import type { components } from "../../types/api.generated";
import { Button } from "../../components/ui/button";
import { api } from "../chat/stream";
type Document = components["schemas"]["DocumentOut"];
type Config = components["schemas"]["DocumentConfiguration"];
type Job = components["schemas"]["JobOut"];

export function KnowledgePanel({ onAsk }: { onAsk: (id: string) => void }) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [config, setConfig] = useState<Config | null>(null);
  const [jobs, setJobs] = useState<Record<string, Job>>({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [notice, setNotice] = useState("");
  const refresh = useCallback(async () => {
    try {
      const [rows, settings] = await Promise.all([
        api<Document[]>("/documents"),
        api<Config>("/documents/config"),
      ]);
      setDocuments(rows);
      setConfig(settings);
      const active = rows.filter(
        (row) =>
          ["queued", "processing", "embedding"].includes(row.status) &&
          row.current_job_id,
      );
      const states = await Promise.all(
        active.map((row) => api<Job>(`/jobs/${row.current_job_id}`)),
      );
      setJobs(Object.fromEntries(states.map((job) => [job.target_id, job])));
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Unable to load documents.",
      );
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 2000);
    return () => window.clearInterval(timer);
  }, [refresh]);
  const upload = async (file?: File) => {
    if (!file) return;
    if (config && file.size > config.max_upload_bytes) {
      setError("PDF exceeds the upload size limit.");
      return;
    }
    setUploading(true);
    setError("");
    setNotice("");
    try {
      const body = new FormData();
      body.append("file", file);
      const result = await api<components["schemas"]["UploadResult"]>(
        "/documents/upload",
        { method: "POST", body },
      );
      setNotice(
        result.duplicate
          ? "Duplicate PDF: existing document and job reused."
          : "PDF accepted. Worker parsing/indexing asynchronously.",
      );
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  };
  const process = async (
    id: string,
    action: "retry" | "reindex",
    reparse = false,
  ) => {
    setError("");
    try {
      await api(`/documents/${id}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reparse }),
      });
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Job could not start.");
    }
  };
  const remove = async (document: Document) => {
    if (
      !window.confirm(`Delete ${document.filename}, original file and index?`)
    )
      return;
    try {
      await api(`/documents/${document.id}`, { method: "DELETE" });
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Deletion failed.");
    }
  };
  return (
    <section className="knowledge-panel" aria-label="Knowledge Base">
      <div className="document-upload">
        <h2>Your PDF knowledge</h2>
        <p>
          Private files are parsed in the background. Text is sent to your
          configured Embedding provider; answering also uses your LLM.
        </p>
        <label htmlFor="pdf-upload">
          Upload PDF (up to{" "}
          {Math.round((config?.max_upload_bytes ?? 20971520) / 1048576)} MB)
        </label>
        <input
          id="pdf-upload"
          type="file"
          accept="application/pdf,.pdf"
          disabled={uploading}
          onChange={(event) => {
            void upload(event.target.files?.[0]);
            event.target.value = "";
          }}
        />
        {uploading && <p role="status">Uploading…</p>}
        {notice && <p role="status">{notice}</p>}
      </div>
      {config && !config.configured && (
        <div className="configuration-notice" role="status">
          <strong>Embedding configuration required / 请配置 Embedding</strong>
          <p>{config.message}</p>
          <p>
            Parsing can run, but indexing fails until model, dimensions and Key
            are configured. No mock embeddings are used.
          </p>
        </div>
      )}
      {error && (
        <div role="alert" className="health-error">
          <p>{error}</p>
          <Button
            variant="outline"
            onClick={() => {
              setError("");
              void refresh();
            }}
          >
            Retry document list
          </Button>
        </div>
      )}
      {loading && <p>Loading documents…</p>}
      {!loading && !documents.length && (
        <div className="chat-empty">
          <h2>No PDFs yet</h2>
          <p>
            Upload a text-based PDF. Scans, encrypted files and textless pages
            require review; OCR is unavailable.
          </p>
        </div>
      )}
      <div className="document-list">
        {documents.map((document) => (
          <article
            className="document-card"
            key={document.id}
            data-document-id={document.id}
          >
            <h3>{document.filename}</h3>
            <span className={`document-status ${document.status}`}>
              {document.status}
            </span>
            <p>
              {document.page_count} pages · {document.chunk_count} chunks ·{" "}
              {document.extracted ? "Text extraction saved" : "Not extracted"}
            </p>
            {jobs[document.id] && (
              <div className="job-progress">
                <label>
                  {jobs[document.id].stage} · {jobs[document.id].progress}%
                </label>
                <progress max={100} value={jobs[document.id].progress} />
              </div>
            )}
            {document.error_code && (
              <p className="document-error">
                {document.error_code}: {document.error_message}
              </p>
            )}
            {document.embedding_model && (
              <small>
                Index: {document.embedding_model} /{" "}
                {document.embedding_dimensions} dimensions
              </small>
            )}
            <div className="document-actions">
              {document.status === "ready" && (
                <Button onClick={() => onAsk(document.id)}>Ask this PDF</Button>
              )}
              {document.status === "failed" && (
                <>
                  <Button
                    variant="outline"
                    onClick={() => void process(document.id, "retry")}
                  >
                    Retry processing
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => void process(document.id, "retry", true)}
                  >
                    Reparse from PDF
                  </Button>
                </>
              )}
              {["ready", "needs_reindex"].includes(document.status) && (
                <Button
                  variant="outline"
                  onClick={() => void process(document.id, "reindex")}
                >
                  Rebuild index
                </Button>
              )}
              <a
                href={`/api/documents/${document.id}/file`}
                target="_blank"
                rel="noreferrer"
              >
                Open original
              </a>
              <Button variant="outline" onClick={() => void remove(document)}>
                Delete PDF
              </Button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
