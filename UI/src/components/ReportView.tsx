import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { Citation } from "./Citation";
import type { CitationEntry } from "../types";

interface Props {
  report: string;
  citations: Record<string, CitationEntry>;
}

/**
 * LLMs sometimes wrap headers in bold: `**## Executive Summary**`.
 * Strip the bold so react-markdown sees a real header. One pass is
 * enough — `#{1,6}` covers `#` through `######`, so a second regex for
 * `###` specifically would be redundant.
 */
function normalizeHeaders(md: string): string {
  return md.replace(/\*\*(#{1,6}\s+[^*\n]+?)\*\*/g, "$1");
}

/**
 * Rewrite `[N]` markers into markdown links so react-markdown renders
 * them as clickable anchors. Unknown markers (hallucinated citations)
 * are left untouched on purpose — we want them visible in the report.
 */
function injectCitationLinks(
  report: string,
  citations: Record<string, CitationEntry>
): string {
  return report.replace(/\[(\d+)\]/g, (match, num) => {
    const entry = citations[num];
    if (!entry) return match;
    return `[${num}](${entry.url})`;
  });
}

/**
 * Split markdown into sections headed by `## `. Text before the first
 * `## ` is dropped (LLMs sometimes prepend a stray sentence).
 */
function splitSections(md: string): { title: string; body: string }[] {
  const sections: { title: string; body: string }[] = [];
  let current: { title: string; body: string } | null = null;

  for (const line of md.split("\n")) {
    const m = line.match(/^##\s+(.+?)\s*$/);
    if (m) {
      if (current) sections.push(current);
      current = { title: m[1], body: "" };
    } else if (current) {
      current.body += line + "\n";
    }
  }
  if (current) sections.push(current);
  return sections;
}

/** Map section title → CSS class for the color bar. */
function sectionClass(title: string): string {
  const t = title.toLowerCase();
  if (t.includes("summary") || t.includes("executive")) return "summary";
  if (t.includes("strength")) return "strengths";
  if (t.includes("weakness")) return "weaknesses";
  if (t.includes("opportunit")) return "opportunities";
  if (t.includes("threat")) return "threats";
  return "summary";
}

export function ReportView({ report, citations }: Props) {
  if (!report) return null;

  // Pipeline: raw LLM text → normalized headers → clickable citations
  // → split into sections → render each with its own color.
  const normalized = normalizeHeaders(report);
  const withLinks = injectCitationLinks(normalized, citations);
  const sections = splitSections(withLinks);

  const indices = Object.keys(citations)
    .map(Number)
    .sort((a, b) => a - b);

  return (
    <div className="report-container">
      {sections.map((s, i) => (
        <section key={i} className={`report-section ${sectionClass(s.title)}`}>
          <h2>{s.title}</h2>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{s.body}</ReactMarkdown>
        </section>
      ))}

      {indices.length > 0 && (
        <section className="sources">
          <h3>Sources</h3>
          <ol className="citation-list">
            {indices.map((i) => (
              <Citation key={i} index={i} entry={citations[String(i)]} />
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}