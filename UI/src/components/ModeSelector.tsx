import type { Mode } from "../types";

interface Props {
  value: Mode;
  onChange: (mode: Mode) => void;
  disabled?: boolean;
}

const OPTIONS: { value: Mode; label: string; sub: string }[] = [
  { value: "competitive", label: "Competitor", sub: "SWOT analysis" },
  { value: "employer", label: "Employer", sub: "Red-flag report" },
];

export function ModeSelector({ value, onChange, disabled }: Props) {
  return (
    <div className="mode-selector" role="tablist">
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          role="tab"
          aria-selected={value === opt.value}
          className={`mode-option ${value === opt.value ? "active" : ""}`}
          onClick={() => !disabled && onChange(opt.value)}
          disabled={disabled}
        >
          <span className="mode-label">{opt.label}</span>
          <span className="mode-sub">{opt.sub}</span>
        </button>
      ))}
    </div>
  );
}