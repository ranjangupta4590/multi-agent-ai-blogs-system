"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { Article } from "@/lib/types";

interface AgentStepState {
  id: string;
  name: string;
  role: string;
  status: "pending" | "running" | "completed" | "error";
  duration_ms?: number;
  summary?: string;
}

const INITIAL_STEPS: AgentStepState[] = [
  { id: "1", name: "Research Planner", role: "Deconstructs topic & generates search queries", status: "pending" },
  { id: "2", name: "Researcher", role: "SSRF-safe web evidence collection", status: "pending" },
  { id: "3", name: "Source Validator", role: "Domain credibility scoring & claim extraction", status: "pending" },
  { id: "4", name: "Content Strategist", role: "Audience alignment, narrative angle & retention hooks", status: "pending" },
  { id: "5", name: "Outline Agent", role: "Hierarchical H1/H2/H3 architecture & word targets", status: "pending" },
  { id: "6", name: "Writer Agent", role: "Full draft creation with inline source citations", status: "pending" },
  { id: "7", name: "Fact Checker", role: "Audits assertions against ground truth evidence", status: "pending" },
  { id: "8", name: "SEO Agent", role: "Keyword coverage, meta tags, schema & readability", status: "pending" },
  { id: "9", name: "Critic Agent", role: "Demanding quality rubric evaluation (0.0 to 10.0)", status: "pending" },
  { id: "10", name: "Revision Editor", role: "Conditional polishing to resolve critic feedback", status: "pending" },
  { id: "11", name: "Publisher & Review", role: "Enforces human review before public BlogPilot publishing", status: "pending" },
];

const AGENT_NAME_TO_STEP: Record<string, number> = {
  ResearchPlanner: 0,
  Researcher: 1,
  SourceValidator: 2,
  ContentStrategist: 3,
  OutlineAgent: 4,
  WriterAgent: 5,
  FactChecker: 6,
  SEOAgent: 7,
  CriticAgent: 8,
  EditorAgent: 9,
  PublisherAgent: 10,
};

export default function ArticleWorkflowProgressPage() {
  const params = useParams();
  const router = useRouter();
  const articleId = params?.id as string;

  const [article, setArticle] = useState<Article | null>(null);
  const [steps, setSteps] = useState<AgentStepState[]>(INITIAL_STEPS);
  const [logs, setLogs] = useState<string[]>([]);
  const [isFinished, setIsFinished] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [showCompletionModal, setShowCompletionModal] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const isGeneratingRef = useRef(false);
  const isMountedRef = useRef(true);
  const lastProcessedStepRef = useRef<Record<string, string>>({});
  const logsEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  const startPolling = useCallback(() => {
    if (pollIntervalRef.current) return;

    const pollProgress = async () => {
      if (!isMountedRef.current) return;
      try {
        const progress = await api.getWorkflowProgress(articleId);
        if (!isMountedRef.current || !progress) return;

        if (["IN_REVIEW", "APPROVED", "PUBLISHED"].includes(progress.status)) {
          setIsFinished(true);
          setIsGenerating(false);
          isGeneratingRef.current = false;
          setSteps((prev) => prev.map((s) => ({ ...s, status: "completed" })));
          setShowCompletionModal(true);
          stopPolling();
          return;
        }

        if (progress.status === "DRAFT") {
          setIsGenerating(false);
          isGeneratingRef.current = false;
          stopPolling();
          return;
        }

        if (progress.status === "GENERATING") {
          setIsGenerating(true);
          isGeneratingRef.current = true;
        }

        if (progress.steps && Array.isArray(progress.steps) && progress.steps.length > 0) {
          setSteps((prevSteps) => {
            const nextSteps = [...prevSteps];
            progress.steps.forEach((stepItem: any) => {
              const idx = AGENT_NAME_TO_STEP[stepItem.agent_name] ?? (stepItem.step_number - 1);
              if (idx >= 0 && idx < nextSteps.length) {
                const mappedStatus = stepItem.status === "COMPLETED" ? "completed" : "running";
                nextSteps[idx] = {
                  ...nextSteps[idx],
                  status: mappedStatus,
                  duration_ms: stepItem.duration_ms || nextSteps[idx].duration_ms,
                };

                const evKey = `${stepItem.agent_name}_${stepItem.status}`;
                if (!lastProcessedStepRef.current[evKey]) {
                  lastProcessedStepRef.current[evKey] = "logged";
                  if (stepItem.status === "RUNNING") {
                    setLogs((l) => [...l, `[Agent] Stage ${idx + 1}/11: ${nextSteps[idx].name} is now RUNNING...`]);
                  } else if (stepItem.status === "COMPLETED") {
                    const durText = stepItem.duration_ms ? ` (${stepItem.duration_ms}ms)` : "";
                    setLogs((l) => [...l, `[Agent] Stage ${idx + 1}/11: ${nextSteps[idx].name} COMPLETED${durText} ✓`]);
                  }
                }
              }
            });
            return nextSteps;
          });
        }
      } catch (e) {
        // Ignore temporary network drops
      }
    };

    pollIntervalRef.current = setInterval(pollProgress, 1000);
    pollProgress();
  }, [articleId, stopPolling]);

  // Main generation trigger function
  const runGeneration = useCallback(async () => {
    if (isGeneratingRef.current) return;
    isGeneratingRef.current = true;
    setIsGenerating(true);
    setError(null);

    // Immediately reflect running state in step 1 so UI enters running state without delay!
    setSteps((prev) =>
      prev.map((step, index) =>
        index === 0 ? { ...step, status: "running" } : { ...step, status: "pending" }
      )
    );
    setLogs((prev) => [
      ...prev,
      `[System] Launching 11-agent autonomous pipeline via LLM Gateway...`,
      `[Agent] Stage 1/11: Research Planner is now RUNNING...`,
    ]);

    startPolling();

    try {
      const updated = await api.generateArticle(articleId);
      if (!isMountedRef.current) return;

      setArticle(updated);
      setIsFinished(true);
      setIsGenerating(false);
      isGeneratingRef.current = false;
      setSteps((prev) => prev.map((s) => ({ ...s, status: "completed" })));
      setLogs((prev) => [
        ...prev,
        `[Workflow Completed] Generated ${updated.word_count} words. Total cost: $${(updated.total_cost_usd || 0).toFixed(4)}. Ready for Human Review!`,
      ]);
      setShowCompletionModal(true);
      stopPolling();
    } catch (err: any) {
      if (!isMountedRef.current) return;

      setIsGenerating(false);
      isGeneratingRef.current = false;
      setError(err.message || "Failed during agent execution.");
      setLogs((prev) => [...prev, `[ERROR] ${err.message}`]);
      stopPolling();
      setSteps((prev) =>
        prev.map((s) => (s.status === "running" ? { ...s, status: "error" } : s))
      );
    }
  }, [articleId, startPolling, stopPolling]);

  // Initial workflow setup on mount
  useEffect(() => {
    isMountedRef.current = true;

    async function initWorkflow() {
      try {
        setLogs((prev) => [...prev, `[System] Loading draft metadata for ID: ${articleId}`]);
        const art = await api.getArticle(articleId);
        if (!isMountedRef.current) return;
        setArticle(art);

        const isAlreadyComplete = ["IN_REVIEW", "APPROVED", "PUBLISHED"].includes(art.status);
        if (isAlreadyComplete) {
          setIsFinished(true);
          setIsGenerating(false);
          setSteps((prev) => prev.map((s) => ({ ...s, status: "completed" })));
          setLogs((prev) => [
            ...prev,
            `[System] Article generation has already completed (${art.word_count} words). Ready for review.`,
          ]);
          return;
        }

        if (art.status === "DRAFT") {
          runGeneration();
        } else if (art.status === "GENERATING") {
          setIsGenerating(true);
          isGeneratingRef.current = true;
          setLogs((prev) => [...prev, `[System] Connected to active generation in progress...`]);
          setSteps((prev) =>
            prev.map((step, index) => (index === 0 ? { ...step, status: "running" } : step))
          );
          startPolling();
        }
      } catch (err: any) {
        if (isMountedRef.current) {
          setError(err.message || "Failed to initialize workflow.");
          setLogs((prev) => [...prev, `[ERROR] ${err.message}`]);
        }
      }
    }

    if (articleId) {
      initWorkflow();
    }

    return () => {
      isMountedRef.current = false;
      stopPolling();
    };
  }, [articleId, runGeneration, startPolling, stopPolling]);

  const handleStopGeneration = async () => {
    if (!confirm(`Are you sure you want to stop generation for this article and return it to Draft?`)) return;
    setIsStopping(true);
    try {
      stopPolling();
      isGeneratingRef.current = false;
      setIsGenerating(false);
      const updated = await api.cancelArticleGeneration(articleId);
      setArticle(updated);
      setSteps((prev) => prev.map((s) => (s.status === "running" ? { ...s, status: "pending" } : s)));
      setLogs((prev) => [...prev, `[System] Generation stopped by user. Article status reset to DRAFT.`]);
      setError("Generation was cancelled. You can restart anytime.");
    } catch (err: any) {
      alert(err.message || "Failed to stop generation.");
    } finally {
      setIsStopping(false);
    }
  };

  return (
    <div style={{ maxWidth: "1000px", margin: "0 auto" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "24px",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div>
          <div style={{ fontSize: "0.8rem", color: "var(--brand-primary)", fontWeight: 700, textTransform: "uppercase" }}>
            Live Agent Orchestration Stepper
          </div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 800, letterSpacing: "-0.02em", marginTop: "2px" }}>
            {article ? article.title : "Generating Blog Content..."}
          </h1>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          {isFinished ? (
            <Link href={`/articles/${articleId}`} className="btn btn-primary" style={{ padding: "10px 20px" }}>
              Open Article Workspace →
            </Link>
          ) : isGenerating ? (
            <>
              <div className="badge badge-info" style={{ padding: "8px 16px", fontSize: "0.85rem" }}>
                <span className="pulse-dot" /> Autonomous Agents Active
              </div>
              <button
                onClick={handleStopGeneration}
                disabled={isStopping}
                className="btn btn-secondary"
                style={{
                  color: "var(--accent-danger)",
                  borderColor: "rgba(239, 68, 68, 0.3)",
                  padding: "8px 16px",
                  fontSize: "0.85rem",
                  fontWeight: 600,
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  cursor: isStopping ? "not-allowed" : "pointer",
                }}
                title="Stop generation and return article to Draft"
              >
                <span>■</span> {isStopping ? "Stopping..." : "Stop Generation"}
              </button>
            </>
          ) : (
            <button
              onClick={runGeneration}
              className="btn btn-primary"
              style={{
                background: "var(--brand-gradient)",
                padding: "8px 20px",
                fontSize: "0.9rem",
                fontWeight: 700,
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <span>✦</span> Start Generation
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="badge-danger" style={{ padding: "14px 18px", borderRadius: "var(--radius-md)", marginBottom: "24px" }}>
          <strong>Execution Notice:</strong> {error}
        </div>
      )}

      {/* Main Two-Column Layout: Stepper & Real-time Console */}
      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "24px" }}>
        {/* Left Column: 11-Agent Step Cards */}
        <div className="card" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: "16px" }}>Pipeline Stages</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {steps.map((s, idx) => {
              const isCompleted = s.status === "completed";
              const isRunning = s.status === "running";
              const isError = s.status === "error";

              return (
                <div
                  key={s.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "12px",
                    padding: "10px 14px",
                    borderRadius: "var(--radius-md)",
                    backgroundColor: isRunning
                      ? "var(--brand-glow)"
                      : isCompleted
                      ? "var(--bg-secondary)"
                      : "transparent",
                    border: isRunning
                      ? "1px solid var(--brand-primary)"
                      : isError
                      ? "1px solid var(--accent-danger)"
                      : "1px solid var(--border-subtle)",
                    transition: "all 0.2s ease",
                  }}
                >
                  <div
                    style={{
                      width: "28px",
                      height: "28px",
                      borderRadius: "50%",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "0.8rem",
                      fontWeight: 700,
                      backgroundColor: isRunning
                        ? "var(--brand-primary)"
                        : isCompleted
                        ? "var(--accent-success)"
                        : isError
                        ? "var(--accent-danger)"
                        : "var(--bg-surface)",
                      color: isRunning || isCompleted || isError ? "#fff" : "var(--text-muted)",
                      border: !isRunning && !isCompleted && !isError ? "1px solid var(--border-subtle)" : "none",
                    }}
                  >
                    {isCompleted ? "✓" : isRunning ? <span className="pulse-dot" style={{ width: "8px", height: "8px", backgroundColor: "#fff" }} /> : isError ? "✕" : idx + 1}
                  </div>

                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <span style={{ fontWeight: 600, fontSize: "0.95rem", color: isRunning ? "var(--brand-primary)" : "var(--text-primary)" }}>
                        {s.name}
                      </span>
                      <span
                        style={{
                          fontSize: "0.75rem",
                          fontWeight: 700,
                          textTransform: "uppercase",
                          color: isRunning
                            ? "var(--brand-primary)"
                            : isCompleted
                            ? "var(--accent-success)"
                            : isError
                            ? "var(--accent-danger)"
                            : "var(--text-muted)",
                        }}
                      >
                        {isRunning ? "RUNNING" : isCompleted ? (s.duration_ms ? `${s.duration_ms}ms` : "DONE") : isError ? "FAILED" : "PENDING"}
                      </span>
                    </div>
                    <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", margin: "2px 0 0 0" }}>
                      {s.role}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Real-time Terminal Log Console */}
        <div
          className="card"
          style={{
            padding: "20px",
            display: "flex",
            flexDirection: "column",
            height: "640px",
            backgroundColor: "#0d1117",
            borderColor: "#30363d",
            fontFamily: "var(--font-mono, monospace)",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              borderBottom: "1px solid #21262d",
              paddingBottom: "12px",
              marginBottom: "12px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ width: "10px", height: "10px", borderRadius: "50%", backgroundColor: "#ff5f56" }} />
              <span style={{ width: "10px", height: "10px", borderRadius: "50%", backgroundColor: "#ffbd2e" }} />
              <span style={{ width: "10px", height: "10px", borderRadius: "50%", backgroundColor: "#27c93f" }} />
              <span style={{ fontSize: "0.8rem", color: "#8b949e", marginLeft: "6px" }}>Orchestrator Terminal</span>
            </div>
            <span style={{ fontSize: "0.75rem", color: "#8b949e" }}>
              {isGenerating ? "Streaming telemetry..." : "Idle"}
            </span>
          </div>

          <div
            style={{
              flex: 1,
              overflowY: "auto",
              fontSize: "0.82rem",
              lineHeight: "1.6",
              color: "#c9d1d9",
              display: "flex",
              flexDirection: "column",
              gap: "4px",
            }}
          >
            {logs.map((log, idx) => {
              const isErr = log.startsWith("[ERROR]");
              const isWorkflowDone = log.startsWith("[Workflow Completed]");
              const isAgent = log.startsWith("[Agent]");
              const isAgentDone = log.includes("COMPLETED");

              return (
                <div
                  key={idx}
                  style={{
                    color: isErr
                      ? "#f85149"
                      : isWorkflowDone
                      ? "#7ee787"
                      : isAgentDone
                      ? "#388bfd"
                      : isAgent
                      ? "#e3b341"
                      : "#8b949e",
                  }}
                >
                  {log}
                </div>
              );
            })}
            <div ref={logsEndRef} />
          </div>
        </div>
      </div>

      {/* Completion Modal Celebration */}
      {showCompletionModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0, 0, 0, 0.75)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
            padding: "20px",
          }}
        >
          <div
            className="card"
            style={{
              maxWidth: "500px",
              width: "100%",
              padding: "36px",
              textAlign: "center",
              boxShadow: "0 24px 48px rgba(0, 0, 0, 0.4)",
              border: "1px solid var(--border-subtle)",
              animation: "fadeIn 0.3s ease-out",
            }}
          >
            <div style={{ fontSize: "3.5rem", marginBottom: "12px" }}>🎉</div>
            <h2 style={{ fontSize: "1.45rem", fontWeight: 800, marginBottom: "8px", color: "var(--text-primary)" }}>
              Blog Generation Completed!
            </h2>
            <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", lineHeight: "1.5", marginBottom: "24px" }}>
              All 11 autonomous agents have finished researching, writing, fact-checking, and optimizing your article.
            </p>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3, 1fr)",
                gap: "12px",
                background: "var(--bg-secondary)",
                padding: "16px",
                borderRadius: "var(--radius-md)",
                marginBottom: "28px",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
                  Words
                </div>
                <div style={{ fontSize: "1.25rem", fontWeight: 800, color: "var(--brand-primary)", marginTop: "2px" }}>
                  {article?.word_count || "Ready"}
                </div>
              </div>
              <div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
                  Agents
                </div>
                <div style={{ fontSize: "1.25rem", fontWeight: 800, color: "var(--accent-success)", marginTop: "2px" }}>
                  11/11
                </div>
              </div>
              <div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
                  Status
                </div>
                <div style={{ fontSize: "0.9rem", fontWeight: 800, color: "var(--text-primary)", marginTop: "6px" }}>
                  In Review
                </div>
              </div>
            </div>

            <div style={{ display: "flex", gap: "12px", justifyContent: "center" }}>
              <button
                onClick={() => router.push(`/articles/${articleId}`)}
                className="btn btn-primary"
                style={{ width: "100%", padding: "12px 24px", fontSize: "1rem", fontWeight: 700 }}
              >
                OK — Open Article Workspace →
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
