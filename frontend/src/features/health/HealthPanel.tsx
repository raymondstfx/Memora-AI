import { t } from "../../i18n";
import { useCallback, useEffect, useRef, useState } from "react";
import { Activity, ArrowUpRight, CheckCircle2, RefreshCw } from "lucide-react";
import { getHealth, type HealthResponse } from "../../lib/api";
import { Button } from "../../components/ui/button";

type State =
  | { status: "loading" }
  | { status: "success"; data: HealthResponse }
  | { status: "error"; message: string };

export function HealthPanel() {
  const [state, setState] = useState<State>({ status: "loading" });
  const pending = useRef<AbortController | null>(null);
  const refresh = useCallback(() => {
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    setState({ status: "loading" });
    const timeout = window.setTimeout(
      () =>
        controller.abort(
          new DOMException(t("Health request timed out."), "TimeoutError"),
        ),
      15000,
    );
    getHealth(controller.signal)
      .then((data) => {
        if (pending.current === controller)
          setState({ status: "success", data });
      })
      .catch((error: unknown) => {
        if (
          pending.current === controller &&
          !(error instanceof DOMException && error.name === "AbortError")
        ) {
          setState({
            status: "error",
            message:
              error instanceof Error
                ? error.message
                : t("Unable to reach the API."),
          });
        }
      })
      .finally(() => window.clearTimeout(timeout));
  }, []);
  useEffect(() => {
    refresh();
    return () => {
      pending.current?.abort();
      pending.current = null;
    };
  }, [refresh]);

  return (
    <section className="health-panel" aria-labelledby="health-title">
      <div className="panel-heading">
        <div className="icon-tile">
          <Activity size={20} />
        </div>
        <div>
          <h2 id="health-title">{t("Local infrastructure")}</h2>
          <p>{t("Live readiness from your API")}</p>
        </div>
        <Button
          variant="outline"
          onClick={refresh}
          disabled={state.status === "loading"}
          aria-label={t("Refresh service health")}
        >
          <RefreshCw size={15} />
          {t("Refresh")}
        </Button>
      </div>
      <div aria-live="polite" aria-busy={state.status === "loading"}>
        {state.status === "loading" && (
          <p className="health-notice">
            {t("Checking API, database, schema and queue connection…")}
          </p>
        )}
        {state.status === "error" && (
          <div className="health-error" role="alert">
            <strong>{t("Services need attention")}</strong>
            <p>{t(state.message)}</p>
            <Button variant="outline" onClick={refresh}>
              {t("Try again")}
            </Button>
          </div>
        )}
        {state.status === "success" && (
          <div className="dependency-grid">
            {Object.entries(state.data.dependencies).map(([name, value]) => (
              <div className="dependency" key={name}>
                <span>
                  {name === "postgres"
                    ? t("PostgreSQL")
                    : name === "pgvector"
                      ? t("pgvector")
                      : name === "schema"
                        ? t("Alembic schema")
                        : t("Redis")}
                </span>
                <span className="ready">
                  <CheckCircle2 size={14} /> {t(value)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="panel-footer">
        <span>{t("Local dependencies · live status")}</span>
        <a href="/docs" target="_blank" rel="noreferrer">
          {t("API reference")}
          <ArrowUpRight size={14} />
        </a>
      </div>
    </section>
  );
}
