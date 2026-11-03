import type { components } from "../../types/api.generated";
export type Citation = components["schemas"]["SourceCitation"];
export function CitationCards({ sources }: { sources: Citation[] }) {
  if (!sources.length) return null;
  return (
    <div className="citation-cards" aria-label="PDF sources">
      {sources.map((source) => (
        <a
          key={source.key}
          href={`/api/documents/${source.document_id}/file#page=${source.page_no}`}
          target="_blank"
          rel="noreferrer"
          className="citation-card"
        >
          <strong>
            [{source.label}] {source.filename} · Page {source.page_no}
          </strong>
          <small>Internal PDF evidence</small>
          <blockquote>{source.excerpt}</blockquote>
        </a>
      ))}
    </div>
  );
}
