const EXAMPLES = ["Stripe", "Notion", "Flipkart", "Figma", "Linear", "Zerodha"];

interface Props {
    onPick: (company: string) => void;
}

export function EmptyState({ onPick }: Props) {
    return (
        <div className="empty-state">
            <div className="hint">Try one of these</div>
            <div className="example-pills">
                {EXAMPLES.map((c) => (
                    <button key={c} className="example-pill" onClick={() => onPick(c)}>
                        {c}
                    </button>
                ))}
            </div>
        </div>
    );
}
