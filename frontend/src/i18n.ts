import { useSyncExternalStore } from "react";
import zh from "./locales/zh.json";
import errors from "./locales/errors.zh.json";
export type Language = "zh" | "en";
const listeners = new Set<() => void>();
function initial(): Language {
  try {
    return localStorage.getItem("memora.language") === "en" ? "en" : "zh";
  } catch {
    return "zh";
  }
}
let language = initial();
export const getLanguage = () => language;
export const getLocale = () => (language === "zh" ? "zh-CN" : "en-US");
export function setLanguage(value: Language) {
  language = value;
  try {
    localStorage.setItem("memora.language", value);
  } catch {
    /* Private browsing may disable storage. */
  }
  document.documentElement.lang = getLocale();
  document.title =
    value === "zh"
      ? "Memora AI · 知识与行动工作区"
      : "Memora AI · Connected workspace";
  listeners.forEach((listener) => listener());
}
export function useLanguage() {
  return useSyncExternalStore((listener) => {
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  }, getLanguage);
}
const catalog: Record<string, string> = zh;
const reverse = Object.fromEntries(
  Object.entries(catalog).map(([key, value]) => [value, key]),
);
// Only explicit UI strings use this function; saved user/model content never does.
export function t(
  key: string,
  values: Record<string, string | number | null | undefined> = {},
) {
  const error = /\(([A-Z][A-Z_0-9]+); ([^)]+)\)$/.exec(key);
  if (language === "zh" && error)
    return (
      errorMessage(error[1], key.slice(0, error.index)) +
      ` (${error[1]}; ${error[2]})`
    );
  // Dynamic configuration messages contain identifiers, never secret values.
  if (language === "zh" && key.startsWith("Configure backend .env: "))
    return "请配置项目根目录 .env：" + key.slice(24);
  const http = /^API returned HTTP (\d+)\. Check backend availability\.$/.exec(
    key,
  );
  if (language === "zh" && http)
    return `接口返回 HTTP ${http[1]}。请检查后端服务。`;
  const retrieved =
    /^Retrieved (\d+) (evidence chunks|memory sources|web sources with retrieval times)\.$/.exec(
      key,
    );
  if (language === "zh" && retrieved)
    return `已检索 ${formatNumber(Number(retrieved[1]))} 条${retrieved[2] === "evidence chunks" ? "证据分块" : retrieved[2] === "memory sources" ? "记忆来源" : "含检索时间的网页来源"}。`;
  const canonical = reverse[key] ?? key;
  const text =
    language === "zh" ? (catalog[canonical] ?? canonical) : canonical;
  return text.replace(/\{(\w+)\}/g, (match, name: string) =>
    typeof values[name] === "number"
      ? formatNumber(values[name])
      : String(values[name] ?? match),
  );
}
export function formatDate(
  value: string,
  timezone = Intl.DateTimeFormat().resolvedOptions().timeZone,
  dateOnly = false,
) {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  return (
    new Intl.DateTimeFormat(getLocale(), {
      timeZone: timezone,
      dateStyle: "medium",
      ...(dateOnly ? {} : { timeStyle: "short" }),
    }).format(date) +
    " · " +
    timezone
  );
}
export function formatNumber(value: number, maximumFractionDigits = 2) {
  return new Intl.NumberFormat(getLocale(), { maximumFractionDigits }).format(
    value,
  );
}
setLanguage(language);

export function validationMessage(target: EventTarget) {
  if (!(
    target instanceof HTMLInputElement ||
    target instanceof HTMLTextAreaElement ||
    target instanceof HTMLSelectElement
  ))
    return;
  target.setCustomValidity("");
  const validity = target.validity;
  if (validity.valid) return;
  target.setCustomValidity(
    t(
      validity.valueMissing
        ? "This field is required."
        : validity.typeMismatch
          ? "Enter a valid value (for example an email address)."
          : validity.rangeOverflow ||
              validity.rangeUnderflow ||
              validity.stepMismatch
            ? "Enter a number within the permitted range."
            : validity.tooShort || validity.tooLong
              ? "Check the permitted text length."
              : "Check the format of this field.",
    ),
  );
}

export function errorMessage(code: string | null | undefined, message = "") {
  if (language === "en") return message || code || "Request failed.";
  const catalog: Record<string, string> = errors;
  return (
    catalog[code ?? ""] ??
    (catalog[
      code?.includes("QUOTA") || code?.includes("RATE_LIMIT")
        ? "PROVIDER_RATE_LIMITED"
        : ""
    ] ||
      "操作失败，请检查配置、服务状态和错误编号后再明确重试。")
  );
}
