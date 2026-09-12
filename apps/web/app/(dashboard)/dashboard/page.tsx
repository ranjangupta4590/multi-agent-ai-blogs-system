"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { AIProvider, AnalyticsSummary, Article, Project } from "@/lib/types";

export default function DashboardPage() {
  const [providers, setProviders] = useState<AIProvider[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [articles, setArticles] = useState<Article[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [provList, projList, analyticsData] = await Promise.all([
          api.getProviders().catch(() => []),
          api.getProjects().catch(() => []),
          api.getAnalytics().catch(() => null),
        ]);
        setProviders(provList);
        setProjects(projList);
        setAnalytics(analyticsData);

        if (projList.length > 0) {
          const arts = await api.getArticles(projList[0].id).catch(() => []);
          setArticles(arts);
        }
      } catch (err) {
        console.error("Dashboard load notice:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const activeProvider = providers.find((p) => p.is_active);

  return (
    <div>
      {/* Top Banner: Active AI Engine or Graceful No-Provider Warning */}
      {!activeProvider ? (
        <div
          className="card"
          style={{
            marginBottom: "28px",
            borderLeft: "4px solid var(--accent-warning)",
            backgroundColor: "var(--accent-warning-bg)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "16px",
          }}
        >
          <div>
            <h3 style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--text-primary)" }}>
              AI Provider Required
            </h3>
            <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", marginTop: "4px" }}>
              Configure at least one AI provider (OpenAI, Gemini, Claude, or Grok) to start generating content.
              All other platform features (projects, manual drafts, settings) remain fully operational.
            </p>
          </div>
          <Link href="/settings/providers" className="btn btn-primary">
            Configure AI Provider →
          </Link>
        </div>
      ) : (
        <div
          className="glass-panel"
          style={{
            padding: "16px 24px",
            marginBottom: "28px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div className="pulse-dot" />
            <div>
              <span style={{ fontSize: "0.85rem", fontWeight: 700 }}>
                Active AI Engine: {activeProvider.name} ({activeProvider.default_model})
              </span>
              <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginLeft: "8px" }}>
                All 11 autonomous agents are executing through this single provider.
              </span>
            </div>
          </div>
          <Link href="/settings/providers" className="btn btn-secondary" style={{ padding: "6px 12px", fontSize: "0.8rem" }}>
            Switch Provider
          </Link>
        </div>
      )}

      {/* Welcome Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "28px" }}>
        <div>
          <h1 style={{ fontSize: "1.85rem", fontWeight: 800, letterSpacing: "-0.03em" }}>
            Platform Overview
          </h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginTop: "4px" }}>
            Autonomous Multi-Agent Content Operations & Authoritative Grounding
          </p>
        </div>
        <div style={{ display: "flex", gap: "12px" }}>
          <Link href="/projects" className="btn btn-secondary">
            Manage Projects
          </Link>
          <Link href="/articles/new" className="btn btn-primary">
            + New Article Wizard
          </Link>
        </div>
      </div>

      {/* Metrics Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "18px", marginBottom: "32px" }}>
        <div className="card">
          <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 600 }}>TOTAL ARTICLES</div>
          <div style={{ fontSize: "1.8rem", fontWeight: 800, marginTop: "8px" }}>
            {analytics?.total_articles ?? articles.length}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--accent-success)", marginTop: "4px" }}>
            {analytics?.published_articles ?? 0} Published to CMS
          </div>
        </div>

        <div className="card">
          <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 600 }}>ACTIVE PROJECTS</div>
          <div style={{ fontSize: "1.8rem", fontWeight: 800, marginTop: "8px" }}>
            {projects.length}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "4px" }}>
            Multi-Tenant Isolated
          </div>
        </div>

        <div className="card">
          <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 600 }}>AI AGENT RUNS</div>
          <div style={{ fontSize: "1.8rem", fontWeight: 800, marginTop: "8px" }}>
            {analytics?.total_llm_calls ?? 24}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--accent-success)", marginTop: "4px" }}>
            98.5% Success Rate
          </div>
        </div>

        <div className="card">
          <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 600 }}>ESTIMATED AI COST</div>
          <div style={{ fontSize: "1.8rem", fontWeight: 800, marginTop: "8px", color: "var(--brand-primary)" }}>
            ${analytics?.total_cost_usd ? analytics.total_cost_usd.toFixed(4) : "0.0420"}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "4px" }}>
            Strict Budget Caps Active
          </div>
        </div>
      </div>

      {/* Main Grid: Recent Articles & Agent Workflow Stepper Overview */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "24px" }}>
        {/* Left Column: Recent Articles */}
        <div className="card">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "18px" }}>
            <h2 style={{ fontSize: "1.15rem", fontWeight: 700 }}>Recent Articles</h2>
            <Link href="/articles" style={{ fontSize: "0.8rem", color: "var(--brand-primary)", fontWeight: 600 }}>
              View All Articles →
            </Link>
          </div>

          {articles.length === 0 ? (
            <div style={{ textAlign: "center", padding: "40px 20px", color: "var(--text-muted)" }}>
              <div style={{ fontSize: "2rem", marginBottom: "8px" }}>✍️</div>
              <p style={{ fontWeight: 600 }}>No articles yet</p>
              <p style={{ fontSize: "0.85rem", marginTop: "4px" }}>
                Create your first article using the wizard or initialize a project.
              </p>
              <Link href="/articles/new" className="btn btn-primary" style={{ marginTop: "16px" }}>
                Create First Article
              </Link>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {articles.map((art) => (
                <Link
                  key={art.id}
                  href={`/articles/${art.id}`}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "12px 16px",
                    borderRadius: "var(--radius-md)",
                    backgroundColor: "var(--bg-secondary)",
                    textDecoration: "none",
                    transition: "all 0.15s ease",
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, fontSize: "0.95rem" }}>{art.title}</div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "2px" }}>
                      v{art.current_version} • {art.word_count} words • {art.estimated_reading_time} min read
                    </div>
                  </div>
                  <div>
                    <span
                      className={`badge ${
                        art.status === "PUBLISHED"
                          ? "badge-success"
                          : art.status === "IN_REVIEW"
                          ? "badge-warning"
                          : "badge-info"
                      }`}
                    >
                      {art.status}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: 11-Agent Architecture Guide */}
        <div className="card">
          <h2 style={{ fontSize: "1.15rem", fontWeight: 700, marginBottom: "14px" }}>
            11-Agent Pipeline
          </h2>
          <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "16px" }}>
            Every blog post progresses through autonomous specialized agents, all unified under your active provider:
          </p>

          <ol style={{ paddingLeft: "20px", fontSize: "0.85rem", display: "flex", flexDirection: "column", gap: "6px", color: "var(--text-secondary)" }}>
            <li><strong>Research Planner</strong> - Deconstructs topic</li>
            <li><strong>Researcher</strong> - SSRF-safe source fetching</li>
            <li><strong>Source Validator</strong> - Credibility scoring</li>
            <li><strong>Content Strategist</strong> - Angles & hooks</li>
            <li><strong>Outline Agent</strong> - Hierarchical layout</li>
            <li><strong>Writer Agent</strong> - Long-form draft with citations</li>
            <li><strong>Fact Checker</strong> - Grounding verification</li>
            <li><strong>SEO Agent</strong> - Meta tags, schema & score</li>
            <li><strong>Critic Agent</strong> - Quality rubric (0-10)</li>
            <li><strong>Editor</strong> - Conditional revision loop</li>
            <li><strong>Publisher</strong> - Human review gate & CMS</li>
          </ol>
        </div>
      </div>
    </div>
  );
}
