import type { Mode } from "../types";

const EXAMPLES: Record<Mode, string[]> = {
    competitive: ["Walmart", "NVIDIA", "JP Morgan", "Citi", "Amazon"],
    employer: ["Infosys", "TCS", "Wipro", "Zoho", "Accenture", "Cognizant"],
}

interface Props {
    onPick: (company: string) => void;
    mode: Mode;
}

export function EmptyState({ onPick, mode }: Props) {
    return (
        <div className="empty-state">
            <div className="hint">Try one of these</div>
            <div className="example-pills">
                {EXAMPLES[mode].map((c) => (
                    <button key={c} className="example-pill" onClick={() => onPick(c)}>
                        {c}
                    </button>
                ))}
            </div>
        </div>
    );
}
