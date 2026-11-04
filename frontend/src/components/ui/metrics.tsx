import type { LucideIcon } from "lucide-react";
import { t, formatNumber } from "../../i18n";
export function Metrics({
  items,
}: {
  items: {
    label: string;
    value: number | string | null;
    icon: LucideIcon;
    hint?: string;
  }[];
}) {
  return (
    <div className="metric-grid">
      {items.map(({ label, value, icon: Icon, hint }) => (
        <div className="metric-card" key={label}>
          <div>
            <span>{t(label)}</span>
            <Icon size={19} />
          </div>
          <strong>
            {value === null
              ? "—"
              : typeof value === "number"
                ? formatNumber(value)
                : value}
          </strong>
          {hint && <small>{t(hint)}</small>}
        </div>
      ))}
    </div>
  );
}
