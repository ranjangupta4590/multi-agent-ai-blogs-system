"use client";

import React, { useEffect, useRef, useState } from "react";
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

export default function ArticleWorkflowProgressPage() {
  const params = useParams();
  const router = useRouter();
  const articleId = params?.id as string;

  const [article, setArticle] = useState<Article | null>(null);
  const [steps, setSteps] = useState<AgentStepState[]>(INITIAL_STEPS);
  const [logs, setLogs] = useState<string[]>([]);
  const [isFinished, setIsFinished] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const executionStartedRef = useRef(false);

  useEffect(() => {
    if (!articleId || executionStartedRef.current) return;
    executionStartedRef.current = true;

    let isMounted = true;

    async function startExecution() {
      try {
        setLogs((prev) => [...prev, `[System] Fetching initial draft metadata for ID: ${articleId}`]);
        const art = await api.getArticle(articleId);
        if (isMounted) setArticle(art);
        if (art.status !== "DRAFT") {
          if (isMounted) {
            const completed = ["IN_REVIEW", "APPROVED", "PUBLISHED"].includes(art.status);
            setIsFinished(completed);
            setSteps((prev) => prev.map((step, index) => completed ? { ...step, status: "completed" } : index === 0 ? { ...step, status: "running" } : step));
            setLogs((prev) => [...prev, completed
              ? `[System] This article was already generated (${art.word_count} words). Ready for review.`
              : `[System] A generation is already in progress. This page will not start a duplicate run.`]);
            if (!completed) setError("Generation is already in progress. Refresh later to see the completed article.");
          }
          return;
        }

        setLogs((prev) => [...prev, `[System] Triggering 11-agent pipeline via active model gateway...`]);
        setSteps((prev) => prev.map((step, index) => index === 0 ? { ...step, status: "running" } : step));

        // Trigger the actual backend generation workflow
        const updatedArticle = await api.generateArticle(articleId);
        if (isMounted) {
          setArticle(updatedArticle);
          setIsFinished(true);
          setSteps((prev) => prev.map((s) => ({ ...s, status: "completed" })));
          setLogs((prev) => [
            ...prev,
            `[Workflow Completed] Generated ${updatedArticle.word_count} words. Total cost: $${updatedArticle.total_cost_usd.toFixed(4)}. Ready for Human Review!`,
          ]);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || "Failed during agent execution.");
          setSteps((prev) => prev.map((step, index) => index === 0 ? { ...step, status: "error", summary: "Generation failed before the workflow completed." } : step));
          setLogs((prev) => [...prev, `[ERROR] ${err.message}`]);
        }
      }
    }

    startExecution();

    return () => {
      isMounted = false;
    };
  }, [articleId]);

  return (
    <div style={{ maxWidth: "1000px", margin: "0 auto" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "24px" }}>
        <div>
          <div style={{ fontSize: "0.8rem", color: "var(--brand-primary)", fontWeight: 700, textTransform: "uppercase" }}>
            Live Agent Orchestration Stepper
          </div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 800, letterSpacing: "-0.02em", marginTop: "2px" }}>
            {article ? article.title : "Generating Blog Content..."}
          </h1>
        </div>

        {isFinished ? (
          <Link href={`/articles/${articleId}`} className="btn btn-primary" style={{ padding: "10px 20px" }}>
            Open Article Workspace →
          </Link>
        ) : (
          <div className="badge badge-info" style={{ padding: "8px 16px", fontSize: "0.85rem" }}>
            <span className="pulse-dot" /> Autonomous Agents Active
          </div>
        )}
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
                      : "1px solid var(--border-subtle)",
                    transition: "all 0.2s ease",
                  }}
                >
                  <div
                    style={{
                      width: "28px",
                      height: "28px",
                      borderRadius: "50%",
                      background: isCompleted
                        ? "var(--accent-success)"
                        : isRunning
                        ? "var(--brand-primary)"
                        : "var(--bg-secondary)",
                      color: "#fff",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "0.8rem",
                      fontWeight: 700,
                      flexShrink: 0,
                    }}
                  >
                    {isCompleted ? "✓" : isRunning ? "●" : idx + 1}
                  </div>

                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: "0.9rem", color: isRunning ? "var(--brand-primary)" : "var(--text-primary)" }}>
                      {s.name}
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                      {s.role}
                    </div>
                  </div>

                  <div>
                    {isCompleted ? (
                      <span className="badge badge-success" style={{ fontSize: "0.7rem" }}>Passed</span>
                    ) : isRunning ? (
                      <span className="badge badge-info" style={{ fontSize: "0.7rem" }}>Running...</span>
                    ) : (
                      <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Pending</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Console Stream */}
        <div className="card" style={{ padding: "24px", display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
            <h2 style={{ fontSize: "1.1rem", fontWeight: 700 }}>Telemetry Console</h2>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
              {logs.length} events logged
            </span>
          </div>

          <div
            style={{
              flex: 1,
              background: "#0d1117",
              color: "#58a6ff",
              fontFamily: "var(--font-mono)",
              fontSize: "0.8rem",
              padding: "16px",
              borderRadius: "var(--radius-md)",
              border: "1px solid #30363d",
              overflowY: "auto",
              maxHeight: "500px",
              display: "flex",
              flexDirection: "column",
              gap: "6px",
            }}
          >
            {logs.map((log, index) => (
              <div key={index} style={{ wordBreak: "break-all" }}>
                {log.startsWith("[ERROR]") ? (
                  <span style={{ color: "#f85149" }}>{log}</span>
                ) : log.startsWith("[Workflow Completed]") ? (
                  <span style={{ color: "#3fb950", fontWeight: 600 }}>{log}</span>
                ) : (
                  <span>{log}</span>
                )}
              </div>
            ))}
          </div>

          {isFinished && (
            <div style={{ marginTop: "16px", textAlign: "center" }}>
              <Link href={`/articles/${articleId}`} className="btn btn-primary" style={{ width: "100%" }}>
                Review Article Draft & Sources →
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
