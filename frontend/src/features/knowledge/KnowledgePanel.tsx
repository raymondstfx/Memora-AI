import { formatNumber, t, errorMessage } from "../../i18n";
import { useCallback, useEffect, useState } from "react";
import type { components } from "../../types/api.generated";
import { Button } from "../../components/ui/button";
import {
  BookOpen,
  FileText,
  Layers,
  ShieldCheck,
  Upload,
  Search,
} from "lucide-react";
import { Metrics } from "../../components/ui/metrics";
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
  const [filter, setFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
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
        cause instanceof Error ? cause.message : t("Unable to load documents."),
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
      setError(t("PDF exceeds the upload size limit."));
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
          ? t("Duplicate PDF: existing document and job reused.")
          : t("PDF accepted. Worker parsing/indexing asynchronously."),
      );
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : t("Upload failed."));
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
      setError(
        cause instanceof Error ? cause.message : t("Job could not start."),
      );
    }
  };
  const remove = async (document: Document) => {
    if (
      !window.confirm(
        t("Delete {0}, original file and index?", { 0: document.filename }),
      )
    )
      return;
    try {
      await api(`/documents/${document.id}`, { method: "DELETE" });
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : t("Deletion failed."));
    }
  };
  return (
    <section className="knowledge-panel" aria-label={t("Knowledge Base")}>
      <Metrics
        items={[
          {
            label: "Documents",
            value: loading ? null : documents.length,
            icon: FileText,
          },
          {
            label: "Indexed pages",
            value: loading
              ? null
              : documents
                  .filter((d) => d.status === "ready")
                  .reduce((n, d) => n + d.page_count, 0),
            icon: BookOpen,
          },
          {
            label: "Vector chunks",
            value: loading
              ? null
              : documents
                  .filter((d) => d.status === "ready")
                  .reduce((n, d) => n + d.chunk_count, 0),
            icon: Layers,
          },
          {
            label: "Ready documents",
            value: loading
              ? null
              : documents.filter((d) => d.status === "ready").length,
            icon: ShieldCheck,
          },
        ]}
      />
      <div className="document-upload surface-card">
        <span className="icon-tile">
          <Upload size={22} />
        </span>
        <h2>{t("Your PDF knowledge")}</h2>
        <p>
          {t(
            "Private files are parsed in the background. Text is sent to your configured Embedding provider; answering also uses your LLM.",
          )}
        </p>
        <label htmlFor="pdf-upload">
          {t("Upload PDF (up to")}{" "}
          {Math.round((config?.max_upload_bytes ?? 20971520) / 1048576)}
          {t("MB)")}
        </label>
        <div className="file-picker">
          <span aria-hidden="true" className="button button-outline">
            {t("Browse PDF")}
          </span>
          <span aria-hidden="true">{t("Choose a file to upload")}</span>
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
        </div>
        {uploading && <p role="status">{t("Uploading…")}</p>}
        {notice && <p role="status">{t(notice)}</p>}
      </div>
      {config && !config.configured && (
        <div className="configuration-notice" role="status">
          <strong>
            {t("Embedding configuration required / 请配置 Embedding")}
          </strong>
          <p>{t(config.message)}</p>
          <p>
            {t(
              "Parsing can run, but indexing fails until model, dimensions and Key are configured. No mock embeddings are used.",
            )}
          </p>
        </div>
      )}
      {error && (
        <div role="alert" className="health-error">
          <p>{t(error)}</p>
          <Button
            variant="outline"
            onClick={() => {
              setError("");
              void refresh();
            }}
          >
            {t("Retry document list")}
          </Button>
        </div>
      )}
      {loading && <p>{t("Loading documents…")}</p>}
      {!loading && !documents.length && (
        <div className="chat-empty">
          <h2>{t("No PDFs yet")}</h2>
          <p>
            {t(
              "Upload a text-based PDF. Scans, encrypted files and textless pages require review; OCR is unavailable.",
            )}
          </p>
        </div>
      )}
      <div className="list-toolbar">
        <label className="search-field">
          <Search size={17} />
          <input
            aria-label={t("Search documents")}
            placeholder={t("Search documents")}
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
        </label>
        <select
          aria-label={t("Document status")}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">{t("All statuses")}</option>
          {[
            "ready",
            "queued",
            "processing",
            "embedding",
            "failed",
            "needs_reindex",
          ].map((v) => (
            <option key={v} value={v}>
              {t(v)}
            </option>
          ))}
        </select>
        <Button variant="outline" onClick={() => void refresh()}>
          {t("Refresh")}
        </Button>
      </div>
      <div className="document-list">
        <div className="document-table-heading">
          <span>{t("Document")}</span>
          <span>{t("Status and index")}</span>
          <span>{t("Actions")}</span>
        </div>
        {!loading &&
          documents.length > 0 &&
          !documents.some(
            (d) =>
              d.filename.toLowerCase().includes(filter.toLowerCase()) &&
              (!statusFilter || d.status === statusFilter),
          ) && <p className="empty-message">{t("No matching documents.")}</p>}
        {documents
          .filter(
            (d) =>
              d.filename.toLowerCase().includes(filter.toLowerCase()) &&
              (!statusFilter || d.status === statusFilter),
          )
          .map((document) => (
            <article
              className="document-card"
              key={document.id}
              data-document-id={document.id}
            >
              <div className="document-identity">
                <span className="icon-tile">
                  <FileText size={20} />
                </span>
                <h3>{document.filename}</h3>
              </div>
              <div className="document-meta">
                <span className={`document-status ${document.status}`}>
                  {t(document.status)}
                </span>
                <p>
                  {formatNumber(document.page_count)}
                  {t("pages ·")}
                  {formatNumber(document.chunk_count)}
                  {t("chunks ·")}{" "}
                  {document.extracted
                    ? t("Text extraction saved")
                    : t("Not extracted")}
                </p>
                {jobs[document.id] && (
                  <div className="job-progress">
                    <label>
                      {t(jobs[document.id].stage)} ·{" "}
                      {formatNumber(jobs[document.id].progress)}%
                    </label>
                    <progress
                      max={100}
                      value={formatNumber(jobs[document.id].progress)}
                    />
                  </div>
                )}
                {document.error_code && (
                  <p className="document-error">
                    {document.error_code}:{" "}
                    {errorMessage(
                      document.error_code,
                      document.error_message ?? "",
                    )}
                  </p>
                )}
                {document.embedding_model && (
                  <small>
                    {t("Index:")}
                    {document.embedding_model} / {document.embedding_dimensions}
                    {t("dimensions")}
                  </small>
                )}
              </div>
              <div className="document-actions">
                {document.status === "ready" && (
                  <Button onClick={() => onAsk(document.id)}>
                    {t("Ask this PDF")}
                  </Button>
                )}
                {document.status === "failed" && (
                  <>
                    <Button
                      variant="outline"
                      onClick={() => void process(document.id, "retry")}
                    >
                      {t("Retry processing")}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => void process(document.id, "retry", true)}
                    >
                      {t("Reparse from PDF")}
                    </Button>
                  </>
                )}
                {["ready", "needs_reindex"].includes(document.status) && (
                  <Button
                    variant="outline"
                    onClick={() => void process(document.id, "reindex")}
                  >
                    {t("Rebuild index")}
                  </Button>
                )}
                <a
                  href={`/api/documents/${document.id}/file`}
                  target="_blank"
                  rel="noreferrer"
                >
                  {t("Open original")}
                </a>
                <Button variant="outline" onClick={() => void remove(document)}>
                  {t("Delete PDF")}
                </Button>
              </div>
            </article>
          ))}
      </div>
    </section>
  );
}
