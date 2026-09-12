"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { AIProvider, Project } from "@/lib/types";

function ArticleWizardContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialProjectId = searchParams.get("project_id") || "";

  const [step, setStep] = useState(1);
  const [projects, setProjects] = useState<Project[]>([]);
  const [providers, setProviders] = useState<AIProvider[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState(initialProjectId);
  const [topic, setTopic] = useState("");
  const [targetAudience, setTargetAudience] = useState("");
  const [contentGoal, setContentGoal] = useState("Educate technical leaders and rank for targeted search queries");
  const [researchDepth, setResearchDepth] = useState("standard");
  const [keywords, setKeywords] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.getProjects().catch(() => []),
      api.getProviders().catch(() => []),
    ]).then(([projs, provs]) => {
      setProjects(projs);
      setProviders(provs);
      if (projs.length > 0 && !selectedProjectId) {
        setSelectedProjectId(projs[0].id);
      }
    });
  }, [selectedProjectId]);

  const activeProvider = providers.find((p) => p.is_active);

  const handleStartGeneration = async () => {
    if (!selectedProjectId) {
      setError("Please select a project.");
      return;
    }
    if (!topic.trim()) {
      setError("Please provide a blog topic.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const keywordList = keywords
        .split(",")
        .map((k) => k.trim())
        .filter(Boolean);

      // Step 1: Create draft
      const draft = await api.createArticleDraft({
        project_id: selectedProjectId,
        topic,
        target_audience: targetAudience || undefined,
        content_goal: contentGoal,
        research_depth: researchDepth,
        target_keywords: keywordList,
      });

      // Redirect to live workflow stepper view for this article
      router.push(`/articles/${draft.id}/workflow`);
    } catch (err: any) {
      setError(err.message || "Failed to initialize article workflow");
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: "760px", margin: "0 auto" }}>
      {/* Wizard Header */}
      <div style={{ marginBottom: "28px", textAlign: "center" }}>
        <h1 style={{ fontSize: "1.85rem", fontWeight: 800, letterSpacing: "-0.03em" }}>
          Article Generation Wizard
        </h1>
        <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginTop: "4px" }}>
          Configure editorial parameters for the autonomous 11-agent pipeline.
        </p>
      </div>

      {/* Stepper Dots */}
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "10px", marginBottom: "32px" }}>
        {[1, 2, 3].map((s) => (
          <div key={s} style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "50%",
                background: step === s ? "var(--brand-primary)" : step > s ? "var(--accent-success)" : "var(--bg-secondary)",
                color: "#fff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 700,
                fontSize: "0.85rem",
                border: "1px solid var(--border-subtle)",
              }}
            >
              {step > s ? "✓" : s}
            </div>
            {s < 3 && <div style={{ width: "40px", height: "2px", background: step > s ? "var(--accent-success)" : "var(--border-subtle)" }} />}
          </div>
        ))}
      </div>

      {error && (
        <div className="badge-danger" style={{ padding: "12px 16px", borderRadius: "var(--radius-md)", marginBottom: "20px" }}>
          {error}
        </div>
      )}

      {/* Wizard Steps */}
      <div className="card" style={{ padding: "32px" }}>
        {step === 1 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            <h2 style={{ fontSize: "1.25rem", fontWeight: 700 }}>Step 1: Topic & Target Project</h2>

            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "6px" }}>
                Target Project / Brand Vertical
              </label>
              <select
                className="select"
                value={selectedProjectId}
                onChange={(e) => setSelectedProjectId(e.target.value)}
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.industry || "General"})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "6px" }}>
                Blog Topic or Headline Idea
              </label>
              <textarea
                className="textarea"
                rows={3}
                placeholder="e.g. Architecting Zero-Trust AI Gateways for Multi-Cloud Enterprise Deployments"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button
                type="button"
                disabled={!topic.trim() || !selectedProjectId}
                onClick={() => setStep(2)}
                className="btn btn-primary"
              >
                Next: Strategy & SEO →
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            <h2 style={{ fontSize: "1.25rem", fontWeight: 700 }}>Step 2: Audience & SEO Targeting</h2>

            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "6px" }}>
                Target Audience & Reader Profile
              </label>
              <input
                type="text"
                className="input"
                placeholder="e.g. Senior Security Engineers, CTOs, and Infrastructure Architects"
                value={targetAudience}
                onChange={(e) => setTargetAudience(e.target.value)}
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "6px" }}>
                Target Search Keywords (comma separated)
              </label>
              <input
                type="text"
                className="input"
                placeholder="zero-trust ai, llm gateway security, multi-cloud architecture"
                value={keywords}
                onChange={(e) => setKeywords(e.target.value)}
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "6px" }}>
                Research Depth
              </label>
              <select
                className="select"
                value={researchDepth}
                onChange={(e) => setResearchDepth(e.target.value)}
              >
                <option value="brief">Brief (Rapid synthesis, 3-4 core sources)</option>
                <option value="standard">Standard (Comprehensive balance, 5-8 sources)</option>
                <option value="deep">Deep Dive (Exhaustive academic & documentation inquiry)</option>
              </select>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <button type="button" onClick={() => setStep(1)} className="btn btn-secondary">
                ← Back
              </button>
              <button type="button" onClick={() => setStep(3)} className="btn btn-primary">
                Next: Review & Generate →
              </button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            <h2 style={{ fontSize: "1.25rem", fontWeight: 700 }}>Step 3: Verification & Execution</h2>

            <div style={{ background: "var(--bg-secondary)", padding: "18px", borderRadius: "var(--radius-md)" }}>
              <div style={{ fontSize: "0.8rem", textTransform: "uppercase", color: "var(--text-muted)", fontWeight: 700, marginBottom: "8px" }}>
                Selected Parameters Summary
              </div>
              <div style={{ fontSize: "0.9rem", display: "flex", flexDirection: "column", gap: "6px" }}>
                <div><strong>Topic:</strong> {topic}</div>
                <div><strong>Audience:</strong> {targetAudience || "Default from project"}</div>
                <div><strong>Research Depth:</strong> {researchDepth.toUpperCase()}</div>
                <div><strong>Target Keywords:</strong> {keywords || "Auto-extracted"}</div>
              </div>
            </div>

            {/* AI Engine Status Callout */}
            <div
              style={{
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-md)",
                padding: "16px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <div>
                <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 600 }}>DISPATCH ENGINE</div>
                {activeProvider ? (
                  <div style={{ fontSize: "1rem", fontWeight: 700, color: "var(--brand-primary)", marginTop: "2px", display: "flex", alignItems: "center", gap: "8px" }}>
                    <span className="pulse-dot" /> {activeProvider.name} ({activeProvider.default_model})
                  </div>
                ) : (
                  <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--accent-warning)", marginTop: "2px" }}>
                    ⚠️ No Active Provider Selected
                  </div>
                )}
              </div>
              <Link href="/settings/providers" className="btn btn-secondary" style={{ fontSize: "0.8rem" }}>
                Change Provider
              </Link>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", marginTop: "10px" }}>
              <button type="button" onClick={() => setStep(2)} className="btn btn-secondary">
                ← Back
              </button>
              <button
                type="button"
                disabled={loading}
                onClick={handleStartGeneration}
                className="btn btn-primary"
                style={{ padding: "10px 24px" }}
              >
                {loading ? "Initializing Agents..." : "🚀 Launch 11-Agent Workflow"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ArticleWizardPage() {
  return (
    <Suspense fallback={<div style={{ textAlign: "center", padding: "40px" }}>Loading Wizard...</div>}>
      <ArticleWizardContent />
    </Suspense>
  );
}
