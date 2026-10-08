import type { CitationEntry } from "../types";

interface Props {
    index: number;
    entry: CitationEntry;
}

/** Favicon service */
function faviconFor(url: string): string {
    try {
        const domain = new URL(url).hostname;
        return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
    } catch {
        return "";
    }
}

/** Show pmly the domain + path for readability */
function shortUrl(url: string): string {
    try {
        const u = new URL(url);
        const path = u.pathname.length > 1 ? u.pathname : "";
        return u.hostname.replace(/^www\./, "") + path.slice(0, 40);
    } catch {
        return url.slice(0, 60);
    }
}

export function Citation({ index, entry}: Props) {
    return (
        <li className="citation">
            <span className="citation-index">[{index}]</span>
            <img
                className="citation-favicon"
                src={faviconFor(entry.url)}
                alt=""
                loading="lazy"
                onError={(e) => ((e.target as HTMLImageElement).style.visibility = "hidden")}
            />
            <a
                href={entry.url}
                target="_blank"
                rel="noopener noreferrer"
                className="citation-link"
                title={entry.url}
            >
                {shortUrl(entry.url)}
            </a>
            <span className="citation-task">{entry.task_id}</span>
        </li>
    );
}