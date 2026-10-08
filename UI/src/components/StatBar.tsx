interface Props {
    company: string;
    taskCOunt: number;
    sourceCount: number;
    durationMs: number;
}

export function StatBar({ company, taskCount, sourceCount, durationMs }: Props) {
    const seconds = (durationMs / 1000).toFixed(1);

    return (
        <div className="stat-bar">
            <div className="stat">
                <span className="stat-label">Company</span>
                <span className="stat-value accent">{company}</span>
            </div>
            <div className="stat">
                <span className="stat-label">Sub-tasks</span>
                <span className="stat-value">{taskCount}</span>
            </div>
            <div className="stat">
                <span className="stat-label">Sources</span>
                <span className="stat-value">{sourceCount}</span>
            </div>
            <div className="stat">
                <span className="stat-label">Duration</span>
                <span className="stat-value">{seconds}</span>
            </div>
        </div>
    );
}