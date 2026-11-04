import { t, useLanguage, setLanguage, validationMessage } from "../i18n";
import { lazy, Suspense, useEffect, useState } from "react";
import {
  ArrowUpRight,
  BookOpen,
  Brain,
  CheckSquare,
  ChevronRight,
  CircleHelp,
  FileSliders,
  Home,
  Menu,
  MessageSquare,
  Mic,
  Plus,
  Settings,
  ShieldCheck,
  X,
} from "lucide-react";
import { HealthPanel } from "../features/health/HealthPanel";
import { Button } from "../components/ui/button";
import { ChatPanel } from "../features/chat/ChatPanel";
import { MeetingPanel } from "../features/meetings/MeetingPanel";
import { MemoryPanel } from "../features/memory/MemoryPanel";
import { ActionsPanel } from "../features/meetings/ActionsPanel";
import { KnowledgePanel } from "../features/knowledge/KnowledgePanel";
import { Overview } from "./Overview";
const PresentationPanel = lazy(() =>
  import("../features/presentations/PresentationPanel").then((m) => ({
    default: m.PresentationPanel,
  })),
);
const pages = [
  {
    title: "Overview",
    icon: Home,
    description: "From scattered information to traceable decisions.",
  },
  {
    title: "Chat",
    icon: MessageSquare,
    description: "A conversation with everything you know.",
  },
  {
    title: "Knowledge Base",
    icon: BookOpen,
    description:
      "Upload documents. Find answers grounded in the original pages.",
  },
  {
    title: "Meetings",
    icon: Mic,
    description: "Turn conversations into clarity.",
  },
  {
    title: "Memory",
    icon: Brain,
    description: "Keep the context that matters.",
  },
  {
    title: "Tasks & Actions",
    icon: CheckSquare,
    description: "Review the evidence. Approve every action.",
  },
  {
    title: "Presentations",
    icon: FileSliders,
    description: "Bring your evidence into an editable presentation.",
  },
  {
    title: "Settings",
    icon: Settings,
    description: "Your local workspace, connected.",
  },
];
function initialPage() {
  const value = new URLSearchParams(location.search).get("page");
  return pages.some((p) => p.title === value) ? value! : "Chat";
}
export function App() {
  const language = useLanguage();
  const [active, setActive] = useState(initialPage);
  const [menuOpen, setMenuOpen] = useState(false);
  const [chatVersion, setChatVersion] = useState(0);
  const page = pages.find((p) => p.title === active)!;
  const navigate = (title: string) => {
    setActive(title);
    setMenuOpen(false);
    const url = new URL(location.href);
    url.searchParams.set("page", title);
    window.history.pushState(null, "", url);
    window.scrollTo({ top: 0 });
  };
  useEffect(() => {
    const pop = () => {
      setActive(initialPage());
      setMenuOpen(false);
    };
    window.addEventListener("popstate", pop);
    return () => window.removeEventListener("popstate", pop);
  }, []);
  useEffect(() => {
    if (!menuOpen) return;
    const close = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenuOpen(false);
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [menuOpen]);
  return (
    <div
      className={`workspace page-${active.toLowerCase().replaceAll(" ", "-")}`}
      onInvalidCapture={(e) => validationMessage(e.target)}
      onInputCapture={(e) => {
        const el = e.target;
        if (
          el instanceof HTMLInputElement ||
          el instanceof HTMLTextAreaElement ||
          el instanceof HTMLSelectElement
        )
          el.setCustomValidity("");
      }}
    >
      <a href="#main" className="skip-link">
        {t("Skip to content")}
      </a>
      {menuOpen && (
        <button
          className="nav-backdrop"
          aria-label={t("Dismiss navigation")}
          onClick={() => setMenuOpen(false)}
        />
      )}
      <aside className={`sidebar ${menuOpen ? "is-open" : ""}`}>
        <button className="brand" onClick={() => navigate("Overview")}>
          <span className="brand-mark">
            <BookOpen size={23} />
          </span>
          <span>
            MemoraAI<small>{t("Your connected second brain")}</small>
          </span>
        </button>
        <Button
          className="new-synthesis"
          onClick={() => {
            const url = new URL(location.href);
            url.searchParams.delete("conversation");
            url.searchParams.delete("documents");
            window.history.replaceState(null, "", url);
            setChatVersion((v) => v + 1);
            navigate("Chat");
          }}
        >
          <Plus size={18} />
          {t("New synthesis")}
        </Button>
        <p className="nav-label">{t("WORKSPACE")}</p>
        <nav aria-label={t("Main navigation")}>
          {pages
            .filter((p) => p.title !== "Settings")
            .map((item) => (
              <button
                key={item.title}
                className={`nav-item ${active === item.title ? "active" : ""}`}
                aria-current={active === item.title ? "page" : undefined}
                onClick={() => navigate(item.title)}
              >
                <item.icon size={19} />
                <span>{t(item.title)}</span>
                {active === item.title && <span className="nav-dot" />}
              </button>
            ))}
        </nav>
        <div className="sidebar-bottom">
          <button
            className={`nav-item ${active === "Settings" ? "active" : ""}`}
            aria-current={active === "Settings" ? "page" : undefined}
            onClick={() => navigate("Settings")}
          >
            <Settings size={19} />
            {t("Settings")}
          </button>
          <a
            className="help-link"
            href="https://github.com/raymondstfx/Memora-AI#readme"
            target="_blank"
            rel="noreferrer"
          >
            <CircleHelp size={19} />
            {t("Project guide")}
            <ArrowUpRight size={14} />
          </a>
          <div className="profile">
            <span className="profile-avatar">M</span>
            <span>
              {t("Personal workspace")}
              <small>{t("Local development")}</small>
            </span>
            <span className="status-dot" />
          </div>
        </div>
      </aside>
      <div className="main-wrap">
        <header className="topbar">
          <div className="breadcrumbs">
            <button
              className="mobile-menu"
              aria-label={
                menuOpen ? t("Close navigation") : t("Open navigation")
              }
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen(!menuOpen)}
            >
              {menuOpen ? <X size={21} /> : <Menu size={21} />}
            </button>
            <span className="top-brand">MemoraAI</span>
            <ChevronRight size={14} />
            <strong>{t(active)}</strong>
            <span className="trust-label">
              <ShieldCheck size={15} />
              {t("Evidence-linked workspace")}
            </span>
          </div>
          <div className="topbar-actions">
            <div
              className="language-switch"
              role="group"
              aria-label={t("Interface language")}
            >
              <button
                lang="zh-CN"
                aria-pressed={language === "zh"}
                onClick={() => setLanguage("zh")}
              >
                中文
              </button>
              <span>/</span>
              <button
                lang="en"
                aria-pressed={language === "en"}
                onClick={() => setLanguage("en")}
              >
                English
              </button>
            </div>
            <Button
              variant="outline"
              className="artifact-action"
              onClick={() => navigate("Presentations")}
            >
              <Plus size={16} />
              {t("Create presentation")}
            </Button>
          </div>
        </header>
        <main id="main">
          <div className="page-heading">
            <div>
              <div className="page-eyebrow">MEMORA / {t("Workspace")}</div>
              <h1>
                {active === "Settings" ? t("Workspace settings") : t(active)}
              </h1>
              <p className="page-description">{t(page.description)}</p>
            </div>
            <span className="outline-badge">
              <ShieldCheck size={14} />
              {t("Sources stay connected")}
            </span>
          </div>
          {active === "Overview" && <Overview onNavigate={navigate} />}
          {active === "Chat" && <ChatPanel key={chatVersion} />}
          {["Meetings", "Memory"].includes(active) && (
            <div
              className="section-tabs"
              role="group"
              aria-label={t("Meeting and memory views")}
            >
              <button
                aria-pressed={active === "Meetings"}
                onClick={() => navigate("Meetings")}
              >
                <Mic size={16} />
                {t("Meeting analysis")}
              </button>
              <button
                aria-pressed={active === "Memory"}
                onClick={() => navigate("Memory")}
              >
                <Brain size={16} />
                {t("Memory timeline")}
              </button>
            </div>
          )}
          {active === "Meetings" && <MeetingPanel />}
          {active === "Memory" && <MemoryPanel />}
          {active === "Presentations" && (
            <Suspense
              fallback={<p role="status">{t("Loading presentations…")}</p>}
            >
              <PresentationPanel />
            </Suspense>
          )}
          {active === "Tasks & Actions" && <ActionsPanel />}
          {active === "Knowledge Base" && (
            <KnowledgePanel
              onAsk={(id) => {
                const url = new URL(location.href);
                url.searchParams.set("documents", id);
                url.searchParams.delete("conversation");
                window.history.replaceState(null, "", url);
                navigate("Chat");
              }}
            />
          )}
          {active === "Settings" && (
            <>
              <div className="info-banner">
                <ShieldCheck size={20} />
                <p>
                  {t(
                    "Credentials stay on the backend. Manage provider configuration in the local .env file; secrets are never shown here.",
                  )}
                </p>
              </div>
              <HealthPanel />
            </>
          )}
          <footer className="page-footer">
            <span>MemoraAI</span>
            <span>{t("Information. Understanding. Action.")}</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
