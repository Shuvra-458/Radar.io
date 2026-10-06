import type  { RunState } from "../types";

interface Props {
    state: RunState;
}

export function ProgressPanel({ state }: Props) {
    if (state.status === "idle") return null;

    const completedSet = new Set(state.completedTasks);

    return (
        <div className="progress-panel">
            <div className="progress-header">
                <span className={`status-dot-status-${state.status}`} />
                <span>
                    {state.status === "running" && `Researching ${state.company}...`}
                    {state.status === "complete" && `Completed ${state.company}`}
                    {state.status === "error" && `Failed: ${state.error}`}
                </span>
            </div>

            {state.subTasks.length > 0 && (
                <ul className="task-list">
                    {state.subTasks.map((t) => {
                        const done = completedSet.has(t.id);
                        return (
                            <li key={t.id} className={done ? "task done" : "task"}>
                                <span className="task-marker">{done ? "✓" : "○"}</span>
                                <span className="task-id">{t.id}</span>
                                <span className="task-question">{t.question}</span>
                            </li>
                        );
                    })}
                </ul>
            )}
        </div>
    );
}