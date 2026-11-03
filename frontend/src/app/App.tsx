import { lazy, Suspense, useState } from "react";
import {
  ArrowUpRight,
  BookOpen,
  Brain,
  CheckSquare,
  ChevronRight,
  CircleHelp,
  FileSliders,
  Layers,
  Menu,
  MessageSquare,
  Mic,
  Settings,
  Sparkles,
  X,
} from "lucide-react";
import { HealthPanel } from "../features/health/HealthPanel";
import { Button } from "../components/ui/button";
import { ChatPanel } from "../features/chat/ChatPanel";
import { MeetingPanel } from "../features/meetings/MeetingPanel";
const PresentationPanel = lazy(() =>
  import("../features/presentations/PresentationPanel").then((m) => ({
    default: m.PresentationPanel,
  })),
);
import { MemoryPanel } from "../features/memory/MemoryPanel";
import { ActionsPanel } from "../features/meetings/ActionsPanel";
import { KnowledgePanel } from "../features/knowledge/KnowledgePanel";

const pages = [
  {
    title: "Chat",
    icon: MessageSquare,
    phase: 1,
    text: "A conversation with everything you know.",
    detail: "Streaming conversations with locally persisted history.",
  },
  {
    title: "Knowledge Base",
    icon: BookOpen,
    phase: 2,
    text: "Give your knowledge a place to connect.",
    detail:
      "Upload PDFs, track indexing and ask grounded questions with page citations.",
  },
  {
    title: "Meetings",
    icon: Mic,
    phase: 3,
    text: "Turn conversations into clarity.",
    detail:
      "Transcript analysis, decisions and evidence-backed risks arrive in Phase 3.",
  },
  {
    title: "Memory",
    icon: Brain,
    phase: 4,
    text: "Keep the context that matters.",
    detail:
      "Durable facts, provenance and a history of changes arrive in Phase 5.",
  },
  {
    title: "Tasks & Actions",
    icon: CheckSquare,
    phase: 3,
    text: "Move from insight to action.",
    detail:
      "Reviewable tasks and explicitly approved email delivery arrive in Phase 3.",
  },
  {
    title: "Presentations",
    icon: FileSliders,
    phase: 5,
    text: "Bring your thinking into focus.",
    detail:
      "Editable PowerPoint generation, previews and downloads arrive in Phase 5.",
  },
  {
    title: "Settings",
    icon: Settings,
    phase: 0,
    text: "Your local workspace, connected.",
    detail: "Check the infrastructure supporting your Memora workspace.",
  },
];

export function App() {
  const [active, setActive] = useState("Chat");
  const [menuOpen, setMenuOpen] = useState(false);
  const page = pages.find((item) => item.title === active)!;
  const Icon = page.icon;
  return (
    <div className="workspace">
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <aside className={`sidebar ${menuOpen ? "is-open" : ""}`}>
        <a
          className="brand"
          href="#"
          onClick={() => {
            setActive("Chat");
            setMenuOpen(false);
          }}
        >
          <span className="brand-mark">
            <Layers size={24} />
          </span>
          memora<span className="brand-ai">AI</span>
        </a>
        <div className="workspace-label">
          <span className="workspace-avatar">M</span>
          <span>
            Personal workspace<small>Local development</small>
          </span>
          <ChevronRight size={14} />
        </div>
        <p className="nav-label">WORKSPACE</p>
        <nav aria-label="Main navigation">
          {pages.map((item) => (
            <button
              key={item.title}
              className={`nav-item ${active === item.title ? "active" : ""}`}
              aria-current={active === item.title ? "page" : undefined}
              onClick={() => {
                setActive(item.title);
                setMenuOpen(false);
              }}
            >
              <item.icon size={19} />
              <span>{item.title}</span>
              {active === item.title && <span className="nav-dot" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="build-card">
            <span className="build-label">
              <span className="status-dot" /> FOUNDATION
            </span>
            <strong>A thoughtful start.</strong>
            <p>Chat and saved sessions. Configure your model to get started.</p>
            <div className="progress-track">
              <span />
            </div>
            <small>Phase 5 of 6</small>
          </div>
          <a
            className="help-link"
            href="https://github.com/raymondstfx/Memora-AI#readme"
            target="_blank"
            rel="noreferrer"
          >
            <CircleHelp size={17} />
            Project guide
            <ArrowUpRight size={14} />
          </a>
          <div className="profile">
            <span className="profile-avatar">L</span>
            <span>
              Local workspace<small>Single-user demo</small>
            </span>
            <span className="local-badge">DEV</span>
          </div>
        </div>
      </aside>
      <div className="main-wrap">
        <header className="topbar">
          <div>
            <button
              className="mobile-menu"
              aria-label={menuOpen ? "Close navigation" : "Open navigation"}
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen(!menuOpen)}
            >
              {menuOpen ? <X size={21} /> : <Menu size={21} />}
            </button>
            <span>Workspace</span>
            <ChevronRight size={14} />
            <strong>{active}</strong>
          </div>
          <span className="phase-badge">
            <span className="status-dot" /> Phase 5 · Research & presentations
          </span>
        </header>
        <main id="main">
          <div className="page-eyebrow">YOUR CONNECTED WORKSPACE</div>
          <div className="page-heading">
            <h1>{active === "Settings" ? "Workspace settings" : active}</h1>
            <span className="outline-badge">
              {[
                "Chat",
                "Knowledge Base",
                "Meetings",
                "Tasks & Actions",
                "Memory",
                "Presentations",
              ].includes(active)
                ? active === "Meetings"
                  ? "Meeting intelligence"
                  : active === "Presentations"
                    ? "Editable slides & previews"
                    : active === "Tasks & Actions"
                      ? "Reviewed actions"
                      : active === "Memory"
                        ? "Evidence-backed memory"
                        : active === "Knowledge Base"
                          ? "PDF knowledge"
                          : "Streaming chat"
                : page.phase === 0
                  ? "Infrastructure"
                  : `Planned · Phase ${page.phase}`}
            </span>
          </div>
          <p className="page-description">
            A little less scattered. A lot more connected.
          </p>
          {![
            "Chat",
            "Knowledge Base",
            "Meetings",
            "Tasks & Actions",
            "Memory",
            "Presentations",
          ].includes(active) && (
            <section className="welcome-card">
              <div className="welcome-copy">
                <span className="small-label">
                  <Sparkles size={15} /> SPACE FOR YOUR NEXT IDEA
                </span>
                <h2>{page.text}</h2>
                <p>{page.detail}</p>
                <span className="foundation-note">
                  <span className="status-dot" />{" "}
                  {page.phase === 0
                    ? "Live infrastructure checks below"
                    : "Coming in a later phase"}
                </span>
              </div>
              <div className="knowledge-art" aria-hidden="true">
                <div className="orbit orbit-one" />
                <div className="orbit orbit-two" />
                <span className="art-node node-one">
                  <BookOpen size={23} />
                </span>
                <span className="art-node node-two">
                  <MessageSquare size={22} />
                </span>
                <span className="art-node node-three">
                  <CheckSquare size={22} />
                </span>
                <span className="art-center">
                  <Layers size={44} strokeWidth={1.4} />
                </span>
                <span className="art-spark">✦</span>
              </div>
            </section>
          )}
          {active === "Chat" && <ChatPanel />}
          {active === "Meetings" && <MeetingPanel />}
          {active === "Memory" && <MemoryPanel />}
          {active === "Presentations" && (
            <Suspense fallback={<p role="status">Loading presentations…</p>}>
              <PresentationPanel />
            </Suspense>
          )}
          {active === "Tasks & Actions" && <ActionsPanel />}
          {active === "Knowledge Base" && (
            <KnowledgePanel
              onAsk={(id) => {
                const url = new URL(window.location.href);
                url.searchParams.set("documents", id);
                url.searchParams.delete("conversation");
                window.history.replaceState(null, "", url);
                setActive("Chat");
              }}
            />
          )}
          {active !== "Settings" &&
            active !== "Chat" &&
            active !== "Knowledge Base" &&
            active !== "Meetings" &&
            active !== "Tasks & Actions" &&
            active !== "Memory" &&
            active !== "Presentations" && (
              <section className="empty-state">
                <span className="empty-icon">
                  <Icon size={25} strokeWidth={1.5} />
                </span>
                <h2>
                  {active === "Chat"
                    ? "Your next chapter starts here"
                    : `Your ${active.toLowerCase()} will live here`}
                </h2>
                <p>
                  {page.detail} This preview contains the navigation shell and
                  local infrastructure.
                </p>
                <Button disabled>
                  <Icon size={16} /> Available in Phase {page.phase}
                </Button>
                <span className="empty-footnote">
                  This feature is unavailable in Phase 1.
                </span>
              </section>
            )}
          <HealthPanel />
          <footer className="page-footer">
            <span>MEMORA AI</span>
            <span>Information. Understanding. Action.</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
