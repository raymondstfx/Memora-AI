import { t, formatDate } from "../../i18n";
import type { components } from "../../types/api.generated";
export type Citation = components["schemas"]["SourceCitation"];
export function CitationCards({ sources }: { sources: Citation[] }) {
  if (!sources.length) return null;
  return (
    <div className="citation-cards" aria-label={t("Evidence sources")}>
      {sources.map((source) => (
        <a
          key={source.key}
          href={
            source.url
              ? source.url
              : source.meeting_id
                ? `/api/meetings/${source.meeting_id}/transcript`
                : source.conversation_id
                  ? `/api/conversations/${source.conversation_id}/messages`
                  : `/api/documents/${source.document_id}/file#page=${source.page_no}`
          }
          target="_blank"
          rel="noreferrer"
          className="citation-card"
        >
          <strong>
            [{source.label}] {source.filename} ·{" "}
            {source.url
              ? t("Web source")
              : source.meeting_id
                ? t("Lines {0}–{1}", {
                    0: source.line_start,
                    1: source.line_end,
                  })
                : source.conversation_id
                  ? t("Saved message")
                  : t("Page {0}", { 0: source.page_no })}
          </strong>
          <small>
            {source.url
              ? t("External web evidence")
              : source.source_type === "user_correction"
                ? t("User correction · original source retained")
                : source.meeting_id
                  ? t("Meeting evidence")
                  : source.conversation_id
                    ? t("Explicit chat assertion")
                    : t("Internal PDF evidence")}
            {source.occurred_at
              ? ` · ${formatDate(source.occurred_at, source.timezone ?? t("UTC"), source.date_precision === "date")}`
              : ""}
            {source.retrieved_at
              ? ` · ${t("Retrieved")} ${formatDate(source.retrieved_at, "UTC")}`
              : ""}
          </small>
          <blockquote>{source.excerpt}</blockquote>
        </a>
      ))}
    </div>
  );
}
