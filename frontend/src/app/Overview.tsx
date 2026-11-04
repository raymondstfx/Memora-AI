import {
  ArrowRight,
  BookOpen,
  Brain,
  FileSliders,
  Mic,
  ShieldCheck,
} from "lucide-react";
import { t } from "../i18n";
import { Button } from "../components/ui/button";
const capabilities = [
  {
    page: "Knowledge Base",
    icon: BookOpen,
    text: "Upload documents. Find answers grounded in the original pages.",
  },
  { page: "Meetings", icon: Mic, text: "Turn conversations into clarity." },
  { page: "Memory", icon: Brain, text: "Keep the context that matters." },
  {
    page: "Presentations",
    icon: FileSliders,
    text: "Bring your evidence into an editable presentation.",
  },
];
export function Overview({
  onNavigate,
}: {
  onNavigate: (page: string) => void;
}) {
  return (
    <div className="overview">
      <section className="overview-hero">
        <span className="outline-badge">
          <ShieldCheck size={14} />
          {t("Your connected second brain")}
        </span>
        <h2>
          {t("Turn scattered knowledge into")} <em>{t("traceable action.")}</em>
        </h2>
        <p>
          {t(
            "Connect documents, meetings and lasting memory. Keep the evidence behind every decision.",
          )}
        </p>
        <div className="hero-actions">
          <Button onClick={() => onNavigate("Chat")}>
            {t("Open workspace")}
            <ArrowRight size={16} />
          </Button>
          <Button
            variant="outline"
            onClick={() => onNavigate("Knowledge Base")}
          >
            {t("Upload your first document")}
          </Button>
        </div>
        <div className="hero-principles">
          <span>{t("Source-linked answers")}</span>
          <span>{t("History preserved")}</span>
          <span>{t("Human-approved email")}</span>
        </div>
      </section>
      <section className="overview-capabilities">
        <span className="page-eyebrow">{t("CONNECTED CAPABILITIES")}</span>
        <h2>{t("From information to understanding.")}</h2>
        <div className="capability-grid">
          {capabilities.map((c) => (
            <button
              className="capability-card"
              key={c.page}
              onClick={() => onNavigate(c.page)}
            >
              <span className="icon-tile">
                <c.icon size={22} />
              </span>
              <h3>{t(c.page)}</h3>
              <p>{t(c.text)}</p>
              <span className="card-link">
                {t("Open workspace")}
                <ArrowRight size={15} />
              </span>
            </button>
          ))}
        </div>
      </section>
      <section className="overview-workflow">
        <h2>{t("An evidence-first workflow")}</h2>
        <div className="workflow-grid">
          {[
            "Collect your sources",
            "Connect facts over time",
            "Review and create",
          ].map((title, i) => (
            <div className="workflow-card" key={title}>
              <span>0{i + 1}</span>
              <h3>{t(title)}</h3>
              <p>
                {t(
                  [
                    "Upload PDFs and dated meeting transcripts.",
                    "Inspect original evidence and preserve changes.",
                    "Review tasks, approve email and build presentations.",
                  ][i],
                )}
              </p>
            </div>
          ))}
        </div>
        <Button variant="outline" onClick={() => onNavigate("Tasks & Actions")}>
          {t("Review tasks and approvals")}
          <ArrowRight size={16} />
        </Button>
      </section>
    </div>
  );
}
