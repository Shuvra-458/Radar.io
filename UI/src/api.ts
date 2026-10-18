const API_BASE = import.meta.env.VITE_BACKEND_URL || "";

import type { Mode, SSEEvent } from "./types";

export interface AnalyzeResponse {
    job_id: string;
    status: string;
}

export async function startAnalysis(company: string, mode: Mode): Promise<AnalyzeResponse> {
    const res = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ company, mode }),
    });
    if (!res.ok) {
        throw new Error(`POST /analyze failed: $[res.status}`);
    }
    return res.json();
}

/**
 * Susbscribe to a job's SSE stream. Calls `onEvent` for every event/
 * Returns a cleanup function that closes the connection.
 */
export function subscribeToJob(
    jobId: string,
    onEvent: (event: SSEEvent) => void,
    onTransportError: (err: Event) => void
): () => void {
    const es = new EventSource(`${API_BASE}/analyze/${jobId}/stream`);

    es.onmessage = (msg) => {
        try {
            const event = JSON.parse(msg.data) as SSEEvent;
            onEvent(event);
            if (event.type === "complete" || event.type === "error") {
                es.close();
            }
        } catch (e) {
            console.error("bad SSE payload", msg.data, e);
        }
    };

    es.onerror = (err) => {
        // EventSource fires onerror on normal close too.
        if (es.readyState === EventSource.CLOSED) return;
        onTransportError(err);
    };

    return () => es.close();
}