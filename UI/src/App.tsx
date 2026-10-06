import { useCallback, useRef, useState } from "react";

import{ startAnalysis, subscribeToJob } from "./api";
import { SearchBox } from "./components/SearchBox";
import { ProgressPanel } from "./components/ProgressPanel";
import { ReportView } from "./components/ReportView";
import type { RunState } from "./types";

const initialState: RunState = {
    jobId: null,
    company: "",
    status: "idle",
    subTasks: [],
    completedTasks: [],
    report: "",
    citations: {},
    error: null,
};

export default function App() {
    const [state, setState] = useState<RunState>(initialState);

    const unsubscribeRef = useRef<(() => void) | null>(null);

    const handleSubmit = useCallback(async (company: string) => {
        unsubscribeRef.current?.();
        unsubscribeRef.current = null;

        setState({ ...initialState, company, status: "running" });

        let jobId: string;
        try {
            const { job_id } = await startAnalysis(company);
            jobId = job_id;
            setState((s) => ({ ...s, jobId })); 
        } catch (e) {
            setState((s) => ({
                ...s,
                status: "error",
                error: e instanceof Error ? e.message : String(e),
            }));
            return;
        }

        unsubscribeRef.current = subscribeToJob(
            jobId,
            (event) => {
                setState((s) => {
                    switch (event.type) {
                        case "start":
                            return s;
                        
                        case "node":
                            if (event.node === "planner") {
                                return { ...s, subTasks: event.sub_tasks };
                            }
                            if (event.node === "researcher" && event.task_id) {
                                return {
                                    ...s,
                                    completedTasks: [...s.completedTasks, event.task_id],
                                };
                            }
                            // synthesizer + citation events dont change visible state
                            return s;
                        
                        case "complete":
                            return {
                                ...s,
                                status: "complete",
                                report: event.report,
                                citations: event.citations,
                            };
                        
                        case "error":
                            return { ...s, status: "error", error: event.message };
                    }
                });
            },
            (err) => {
                console.error("SSE transport error", err);
                setState((s) => ({ ...s, status: "error", error: "connection lost" }));
            }
        );
    }, []);

    return (
        <div className="app">
            <header className="app-header">
                <h1>
                    Radar<span className="dot">.</span>io
                </h1>
                <p className="tagline">
                    Deep competitve intelligence from live web research.
                </p>
            </header>

            <main className="app-main">
                <SearchBox onSubmit={handleSubmit} disabled={state.status === "running"} />

                <ProgressPanel state={state} />

                {state.status === "complete" && state.report && (
                    <ReportView report={state.report} citations={state.citations} />
                )}
            </main>

            <footer className="app-footer">
                Multi-agent research: LangGraph · Groq · Tavily · pgvector 
            </footer>
        </div>
    );
}