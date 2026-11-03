import type { components } from "../../types/api.generated";
export type Citation = components["schemas"]["SourceCitation"];
export function CitationCards({ sources }: { sources: Citation[] }) {
  if (!sources.length) return null;
  return (
    <div className="citation-cards" aria-label="Evidence sources">
      {sources.map((source) => (
        <a
          key={source.key}
          href={
            source.meeting_id
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
            {source.meeting_id
              ? `Lines ${source.line_start}–${source.line_end}`
              : source.conversation_id
                ? "Saved message"
                : `Page ${source.page_no}`}
          </strong>
          <small>
            {source.source_type === "user_correction"
              ? "User correction · original source retained"
              : source.meeting_id
                ? "Meeting evidence"
                : source.conversation_id
                  ? "Explicit chat assertion"
                  : "Internal PDF evidence"}
            {source.occurred_at
              ? ` · ${new Date(source.occurred_at).toISOString()}`
              : ""}
          </small>
          <blockquote>{source.excerpt}</blockquote>
        </a>
      ))}
    </div>
  );
}
