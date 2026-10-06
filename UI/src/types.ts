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

// Every event the SSE stream can emit
export type SSEEvent = 
    | { type: "start"; company: string }
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
      }
    | { type: "error"; message: string };

// The application-level state we render from.
export interface RunState {
    jobId: string | null;
    company: string;
    status: "idle" | "running" | "complete" | "error";
    subTasks: SubTask[];
    completedTasks: string[];
    report: string;
    citations: Record<string, CitationEntry>;
    error: string | null;
}
