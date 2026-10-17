import { useState } from "react";
import type { DimensionScore, Verdict, CitationEntry } from "../types";

interface Props {
  verdict: Verdict;
  citations: Record<string, CitationEntry>;
}

const BADGE: Record<
  Verdict["verdict"],
  { emoji: string; label: string; cls: string }
> = {
  green: { emoji: "🟢", label: "GREEN FLAG", cls: "badge-green" },
  mixed: { emoji: "🟡", label: "MIXED", cls: "badge-mixed" },
  red: { emoji: "🔴", label: "RED FLAG", cls: "badge-red" },
  unknown: { emoji: "⚪", label: "UNKNOWN", cls: "badge-unknown" },
};

const LABELS: Record<string, string> = {
  legitimacy: "Legitimacy",
  compensation: "Compensation",
  payment_reliability: "Payment reliability",
  work_life_balance: "Work-life balance",
  management_quality: "Management quality",
  hiring_integrity: "Hiring integrity",
  job_security: "Job security",
  growth_credibility: "Growth credibility",
};

const CONF_RANK = { high: 0, medium: 1, low: 2 } as const;

function barClass(score: number): string {
  if (score >= 7) return "bar-green";
  if (score >= 4) return "bar-amber";
  return "bar-red";
}

// SAFE HELPER: Parses evidence and makes [1] or 【1】 clickable
function renderEvidence(
  evidence: string | null | undefined,
  citations: Record<string, CitationEntry>
) {
  if (!evidence) return <span>No evidence text provided.</span>;

  const parts = evidence.split(/([\[【]\d+[\]】])/g);
  return parts.map((part, i) => {
    const match = part.match(/[\[【](\d+)[\]】]/);
    if (match) {
      const num = match[1];
      const entry = citations?.[num];
      if (entry) {
        return (
          <a
            key={i}
            href={entry.url}
            target="_blank"
            rel="noopener noreferrer"
            className="evidence-citation"
          >
            {num}
          </a>
        );
      }
    }
    return <span key={i}>{part}</span>;
  });
}

function DimensionRow({
  name,
  dim,
  citations,
}: {
  name: string;
  dim: DimensionScore;
  citations: Record<string, CitationEntry>;
}) {
  const [open, setOpen] = useState(false);
  const label = LABELS[name] ?? name;

  // If confidence is low, it's a placeholder.
  const isPlaceholder = dim.confidence === "low";

  return (
    <li className="dimension">
      <button
        className="dimension-header"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="dimension-label">{label}</span>

        <span className="dimension-bar-track">
          {isPlaceholder ? (
            <span className="dimension-bar-unknown" />
          ) : (
            <span
              className={`dimension-bar-fill ${barClass(dim.score)}`}
              style={{ width: `${dim.score * 10}%` }}
            />
          )}
        </span>

        <span className="dimension-score">
          {isPlaceholder ? "—" : dim.score}
        </span>

        <span className={`dimension-confidence conf-${dim.confidence}`}>
          {dim.confidence}
        </span>
      </button>

      {open && (
        <div className="dimension-evidence">
          <p>{renderEvidence(dim.evidence, citations)}</p>
          {dim.sources && dim.sources.length > 0 ? (
            <div className="dimension-sources">
              Sources:{" "}
              {dim.sources.map((n) => {
                const entry = citations?.[n];
                if (!entry) return `[${n}] `;
                return (
                  <a
                    key={n}
                    href={entry.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="evidence-citation"
                  >
                    [{n}]
                  </a>
                );
              })}
            </div>
          ) : (
            <div className="dimension-sources dimension-sources-empty">
              No sources cited for this dimension.
            </div>
          )}
        </div>
      )}
    </li>
  );
}

export function VerdictPanel({ verdict, citations }: Props) {
  if (!verdict || !verdict.dimensions) return null;

  const badge = BADGE[verdict.verdict] ?? BADGE.mixed;

  const sortedDimensions = Object.entries(verdict.dimensions || {}).sort(
    ([, a], [, b]) => {
      const diff = (CONF_RANK[a.confidence] || 0) - (CONF_RANK[b.confidence] || 0);
      if (diff !== 0) return diff;
      return a.score - b.score;
    }
  );

  return (
    <section className={`verdict-panel ${badge.cls}`}>
      <div className="verdict-header">
        <div className="verdict-badge">
          <span className="verdict-emoji">{badge.emoji}</span>
          <span className="verdict-label">{badge.label}</span>
        </div>
        <div className="verdict-score">
          <span className="verdict-score-value">
            {verdict.overall_score?.toFixed(1) ?? "0.0"}
          </span>
          <span className="verdict-score-max">/10</span>
        </div>
      </div>

      <p className="verdict-summary">{verdict.summary}</p>

      <ul className="dimension-list">
        {sortedDimensions.length === 0 ? (
          <li style={{ color: "var(--text-dim)", padding: "1rem" }}>
            No dimension data available.
          </li>
        ) : (
          sortedDimensions.map(([name, dim]) => (
            <DimensionRow
              key={name}
              name={name}
              dim={dim}
              citations={citations}
            />
          ))
        )}
      </ul>

      <p className="verdict-disclaimer">
        AI summary of public sources (reviews, forums, news). Not legal or
        employment advice. Click on any dimension to see supporting evidence.
      </p>
    </section>
  );
}