export type Mode = "competitive" | "employer";

// A single sub task, as emitted by the planner node.
export interface SubTask {
    id: string;
    question: string;
}

// One citation entry from the final state
export interface CitationEntry {
    url: string;
    task_id: string;
}

export interface DimensionScore {
  score: number;
  evidence: string;
  confidence: "low" | "medium" | "high";
  sources: number[];
}

export interface Verdict {
  dimensions: Record<string, DimensionScore>;
  overall_score: number;
  verdict: "green" | "mixed" | "red" | "unknown";
  summary: string;
}

// Every event the SSE stream can emit
export type SSEEvent = 
    | { type: "start"; company: string; mode: Mode }
    | {
        type: "node";
        node: "planner";
        sub_task_count: number;
        sub_tasks: SubTask[];
      }

    | {
        type: "node";
        node: "researcher";
        task_id: string | null;
        doc_count: number;
      }
    | {
        type: "node";
        node: "synthesizer";
        report_chars: number;
      }
    | { type: "node"; node: "citation" }
    | {
        type: "complete";
        report: string;
        citations: Record<string, CitationEntry>;
        verdict: Verdict | null;
      }
    | { type: "error"; message: string };

// The application-level state we render from.
export interface RunState {
    jobId: string | null;
    company: string;
    mode: Mode;
    status: "idle" | "running" | "complete" | "error";
    subTasks: SubTask[];
    completedTasks: string[];
    report: string;
    citations: Record<string, CitationEntry>;
    verdict: Verdict | null;
    error: string | null;
}
