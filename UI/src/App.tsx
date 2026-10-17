import { useCallback, useRef, useState } from "react";

import { startAnalysis, subscribeToJob } from "./api";
import { SearchBox } from "./components/SearchBox";
import { ModeSelector } from "./components/ModeSelector";
import { ProgressPanel } from "./components/ProgressPanel";
import { ReportView } from "./components/ReportView";
import { VerdictPanel } from "./components/VerdictPanel";
import { StatBar } from "./components/StatBar";
import { EmptyState } from "./components/EmptyState";
import type { Mode, RunState } from "./types";

const initialState: RunState = {
  jobId: null,
  company: "",
  mode: "competitive",
  status: "idle",
  subTasks: [],
  completedTasks: [],
  report: "",
  citations: {},
  verdict: null,
  error: null,
};

export default function App() {
  const [mode, setMode] = useState<Mode>("competitive");
  const [state, setState] = useState<RunState>(initialState);
  
  // 1. Changed to useRef so the SSE closure sees the correct start time
  const startedAtRef = useRef<number | null>(null);
  const [durationMs, setDurationMs] = useState<number>(0);

  const unsubscribeRef = useRef<(() => void) | null>(null);

  const handleSubmit = useCallback(
    async (company: string) => {
      unsubscribeRef.current?.();
      unsubscribeRef.current = null;

      setState({ ...initialState, company, mode, status: "running" });
      
      
      startedAtRef.current = Date.now();
      setDurationMs(0);

      let jobId: string;
      try {
        const { job_id } = await startAnalysis(company, mode);
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
                return s;

              case "complete":
                
                setDurationMs(Date.now() - (startedAtRef.current ?? Date.now()));
                return {
                  ...s,
                  status: "complete",
                  report: event.report,
                  citations: event.citations,
                  verdict: event.verdict,
                };

              case "error":
                return { ...s, status: "error", error: event.message };
            }
          });
        },
        (err) => {
          console.error("SSE transport error", err);
          setState((s) => ({
            ...s,
            status: "error",
            error: "connection lost",
          }));
        }
      );
    },
    
    [mode] 
  );

  const showStatBar =
    state.status === "complete" && Object.keys(state.citations).length > 0;

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="brand">
          Radar<span className="dot">.</span>io
        </h1>
        <p className="tagline">
          {mode === "employer"
            ? "Is this company worth working for? Backed by citations."
            : "Deep competitive intelligence from live web research."}
        </p>
      </header>

      <main className="app-main">
        <ModeSelector
          value={mode}
          onChange={setMode}
          disabled={state.status === "running"}
        />

        <SearchBox
          onSubmit={handleSubmit}
          disabled={state.status === "running"}
          placeholder={
            mode === "employer"
              ? "Enter a company to evaluate as an employer"
              : "Enter a company name (e.g. Stripe, Flipkart, Notion)"
          }
        />

        {state.status === "idle" && (
          <EmptyState onPick={handleSubmit} mode={mode} />
        )}

        {state.status !== "idle" && <ProgressPanel state={state} />}

        {showStatBar && (
          <StatBar
            company={state.company}
            taskCount={state.subTasks.length}
            sourceCount={Object.keys(state.citations).length}
            durationMs={durationMs}
          />
        )}

        {/* Defensive checks for verdict to prevent React crashes */}
        {state.status === "complete" &&
          state.verdict && (
            <VerdictPanel verdict={state.verdict} />
          )}

        {state.status === "complete" && state.report && (
          <ReportView report={state.report} citations={state.citations} />
        )}
      </main>

      <footer className="app-footer">
        <span>LangGraph</span> · <span>Groq</span> · <span>Tavily</span> ·{" "}
        <span>pgvector</span>
      </footer>
    </div>
  );
}