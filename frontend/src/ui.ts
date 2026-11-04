import type { Severity } from "./types";

export const SEV_ORDER: Severity[] = ["critical", "serious", "moderate", "minor"];

export const SEV_STYLE: Record<Severity, { badge: string; box: string; dot: string }> = {
  critical: { badge: "bg-red-100 dark:bg-red-500/15 text-red-700 dark:text-red-300 ring-red-500/30", box: "#ef4444", dot: "bg-red-500" },
  serious: { badge: "bg-orange-100 dark:bg-orange-500/15 text-orange-700 dark:text-orange-300 ring-orange-500/30", box: "#f97316", dot: "bg-orange-500" },
  moderate: { badge: "bg-amber-100 dark:bg-amber-500/15 text-amber-700 dark:text-amber-300 ring-amber-500/30", box: "#f59e0b", dot: "bg-amber-500" },
  minor: { badge: "bg-sky-100 dark:bg-sky-500/15 text-sky-700 dark:text-sky-300 ring-sky-500/30", box: "#38bdf8", dot: "bg-sky-400" },
};

export const CATEGORY_LABEL: Record<string, string> = {
  alt_text: "Image alt text",
  form_label: "Form labels",
  contrast: "Color contrast",
  empty_name: "Link / button names",
  heading: "Headings",
  language: "Page language",
};

export const stripAl = (html: string) => html.replace(/\s*data-al-id="al\d+"/g, "");
