import type { CitationEntry } from "../types";

interface Props {
    index: number;
    entry: CitationEntry;
}

export function Citation({ index, entry }: Props) {
    return (
        <li className="citation">
            <span className="citation-index">[{index}]</span>
            <a
                href={entry.url}
                target="_blank"
                rel="noopener noreferrer"
                className="citation-link"
            >
                {entry.url}
            </a>
            <span className="citation-task">{entry.task_id}</span>
        </li>
    );
}