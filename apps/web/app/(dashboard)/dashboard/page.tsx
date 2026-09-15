"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { AIProvider, AnalyticsSummary, Article, Project } from "@/lib/types";

const pipeline = [
  ["Research Planner", "Topic & search strategy", "0.4s"], ["Researcher", "SSRF-safe evidence collection", "1.2s"],
  ["Source Validator", "Credibility & claim extraction", "0.6s"], ["Content Strategist", "Audience angle & hooks", "0.8s"],
  ["Outline Agent", "Structure & word targets", "0.5s"], ["Writer Agent", "Citation-aware draft", "2.8s"],
  ["Fact Checker", "Grounding verification", "0.9s"], ["SEO Agent", "Search-ready metadata", "0.4s"],
  ["Critic Agent", "Quality rubric", "0.7s"], ["Editor", "Editorial polish", "1.1s"], ["Publisher", "Human review gate", "0.2s"],
];

export default function DashboardPage() {
  const [providers, setProviders] = useState<AIProvider[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [articles, setArticles] = useState<Article[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const [provList, projList, analyticsData] = await Promise.all([
          api.getProviders().catch(() => []), api.getProjects().catch(() => []), api.getAnalytics().catch(() => null),
        ]);
        setProviders(provList); setProjects(projList); setAnalytics(analyticsData);
        if (projList.length > 0) setArticles(await api.getArticles(projList[0].id).catch(() => []));
      } catch (err) { console.error("Dashboard load notice:", err); }
    }
    loadData();
  }, []);

  const activeProvider = providers.find((provider) => provider.is_active);
  const metrics = [
    ["Total articles", analytics?.total_articles ?? articles.length, `${analytics?.published_articles ?? 0} publicly published`, "✎"],
    ["Active projects", projects.length, "Multi-tenant isolated", "▱"],
    ["AI agent runs", analytics?.total_llm_calls ?? 0, "Tracked through the LLM gateway", "✺"],
    ["Estimated AI cost", `$${analytics?.total_cost_usd ? analytics.total_cost_usd.toFixed(4) : "0.0000"}`, "Current tracked usage", "◈"],
  ];

  return (
    <div className="dashboard-page">
      {!activeProvider ? (
        <section className="engine-banner engine-warning">
          <div><span className="eyebrow">AI setup required</span><h2>Connect an AI provider to start the studio.</h2><p>Projects and manual drafts remain available. Configure OpenAI, Gemini, Claude, or Grok when you are ready to generate.</p></div>
          <Link href="/settings/providers" className="btn btn-primary">Configure provider <span>→</span></Link>
        </section>
      ) : (
        <section className="engine-banner">
          <div className="engine-orb">✦</div>
          <div className="engine-copy"><span className="eyebrow"><i className="pulse-dot" /> Active AI engine · {activeProvider.name}</span><h2>{activeProvider.default_model}</h2><p>All 11 specialist agents use this single selected provider through BlogPilot’s secure gateway.</p></div>
          <Link href="/settings/providers" className="btn btn-secondary">Switch provider <span>↗</span></Link>
        </section>
      )}

      <section className="dashboard-heading">
        <div><span className="eyebrow">Content operations</span><h1>Platform overview</h1><p>Research, verification, editorial review, and public publishing in one focused studio.</p></div>
        <div className="dashboard-heading-actions"><Link href="/projects" className="btn btn-secondary">Manage projects</Link><Link href="/articles/new" className="btn btn-primary">✦ New article</Link></div>
      </section>

      <section className="metric-grid">
        {metrics.map(([label, value, detail, icon]) => <article className="metric-card" key={String(label)}><div className="metric-top"><span>{label}</span><b>{icon}</b></div><strong>{value}</strong><small>{detail}</small></article>)}
      </section>

      <section className="dashboard-content-grid">
        <article className="card dashboard-articles-card">
          <header className="section-heading"><div><span className="eyebrow">Library</span><h2>Recent articles</h2><p>Generated drafts, reviews, and published stories.</p></div><Link href="/articles">View all <span>→</span></Link></header>
          {articles.length === 0 ? <div className="dashboard-empty"><span>✦</span><h3>No articles yet</h3><p>Create your first article, then BlogPilot will guide it through the full review pipeline.</p><Link href="/articles/new" className="btn btn-primary">Create first article</Link></div> : <div className="dashboard-article-list">
            {articles.map((article) => <Link key={article.id} href={`/articles/${article.id}`} className="dashboard-article-row"><div><span className={`article-status status-${article.status.toLowerCase()}`}>{article.status.replace("_", " ")}</span><h3>{article.title}</h3><p>v{article.current_version} · {article.word_count} words · {article.estimated_reading_time} min read</p></div><span className="row-arrow">→</span></Link>)}
          </div>}
        </article>
        <aside className="card pipeline-card">
          <header className="section-heading compact"><div><span className="eyebrow">Orchestration</span><h2>11-agent pipeline</h2><p>Deterministic, source-aware workflow.</p></div><span className="pipeline-live">Ready</span></header>
          <ol className="pipeline-list">{pipeline.map(([name, detail, duration], index) => <li key={name}><span>{String(index + 1).padStart(2, "0")}</span><div><strong>{name}</strong><small>{detail}</small></div><em>{duration}</em></li>)}</ol>
          <Link href="/settings/providers" className="pipeline-link">Configure provider & prompts <span>→</span></Link>
        </aside>
      </section>
    </div>
  );
}
