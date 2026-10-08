import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { Citation } from "./Citation";
import type { CitationEntry } from "../types";

interface Props {
  report: string;
  citations: Record<string, CitationEntry>;
}

/** Strip `**## Foo**` → `## Foo` (LLM wraps headers in bold). */
function normalizeHeaders(md: string): string {
  return md.replace(/\*\*(#{1,6}\s+[^*\n]+?)\*\*/g, "$1");
}

/** Rewrite [N] → [N](url) for citations we can resolve. */
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

/** Map a section title to its CSS class. */
function sectionClass(title: string): string {
  const t = title.toLowerCase();
  if (t.includes("executive") || t.includes("summary")) return "summary";
  if (t.includes("strength")) return "strengths";
  if (t.includes("weakness")) return "weaknesses";
  if (t.includes("opportunit")) return "opportunities";
  if (t.includes("threat")) return "threats";
  return "summary";
}

interface Section {
  title: string;
  body: string;
}

/** Split markdown into `## `-headed sections. */
function splitSections(md: string): Section[] {
  const lines = md.split("\n");
  const sections: Section[] = [];
  let current: Section | null = null;

  for (const line of lines) {
    const m = line.match(/^##\s+(.+?)\s*$/);
    if (m) {
      if (current) sections.push(current);
      current = { title: m[1], body: "" };
    } else if (current) {
      current.body += line + "\n";
    }
    // Text before the first `##` is dropped — LLMs sometimes prefix
    // a stray sentence; not worth rendering.
  }
  if (current) sections.push(current);
  return sections;
}

export function ReportView({ report, citations }: Props) {
  if (!report) return null;

  const prepared = injectCitationLinks(normalizeHeaders(report), citations);
  const sections = splitSections(prepared);
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