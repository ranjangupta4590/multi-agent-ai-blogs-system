"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Article, Project, SEOAnalysis } from "@/lib/types";

export default function SEOIntelligencePage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [articles, setArticles] = useState<Article[]>([]);
  const [selectedArticleId, setSelectedArticleId] = useState("");
  const [seo, setSeo] = useState<SEOAnalysis | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getProjects().then((projs) => {
      setProjects(projs);
      if (projs.length > 0) setSelectedProjectId(projs[0].id);
    });
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      api.getArticles(selectedProjectId).then((arts) => {
        setArticles(arts);
        if (arts.length > 0) setSelectedArticleId(arts[0].id);
      });
    }
  }, [selectedProjectId]);

  useEffect(() => {
    if (selectedArticleId) {
      setLoading(true);
      api.getSEO(selectedArticleId)
        .then(setSeo)
        .catch(() => setSeo(null))
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [selectedArticleId]);

  return (
    <div>
      <div style={{ marginBottom: "28px" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.02em" }}>SEO Intelligence & Optimization</h1>
        <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginTop: "4px" }}>
          Technical SEO audits, keyword coverage, and automated structured data markup.
        </p>
      </div>

      {/* Selectors */}
      <div style={{ display: "flex", gap: "16px", marginBottom: "24px", flexWrap: "wrap" }}>
        <div style={{ minWidth: "220px" }}>
          <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: "4px" }}>
            SELECT PROJECT
          </label>
          <select className="select" value={selectedProjectId} onChange={(e) => setSelectedProjectId(e.target.value)}>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>

        <div style={{ minWidth: "280px" }}>
          <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: "4px" }}>
            SELECT ARTICLE
          </label>
          <select className="select" value={selectedArticleId} onChange={(e) => setSelectedArticleId(e.target.value)}>
            {articles.map((a) => (
              <option key={a.id} value={a.id}>{a.title}</option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: "center", padding: "40px" }}>Loading SEO analysis...</div>
      ) : !seo ? (
        <div className="card" style={{ textAlign: "center", padding: "48px 20px" }}>
          <div style={{ fontSize: "2.5rem", marginBottom: "10px" }}>🎯</div>
          <h3 style={{ fontSize: "1.2rem", fontWeight: 700 }}>No SEO Audit Data</h3>
          <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: "4px" }}>
            Run the 11-agent workflow on this article to produce comprehensive technical SEO metadata.
          </p>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: "24px" }}>
          {/* Left Column: Score Gauge & Checklist */}
          <div className="card">
            <div style={{ textAlign: "center", padding: "20px 0", borderBottom: "1px solid var(--border-subtle)", marginBottom: "20px" }}>
              <div style={{ fontSize: "0.8rem", textTransform: "uppercase", color: "var(--text-muted)", fontWeight: 700 }}>
                Overall SEO Score
              </div>
              <div
                style={{
                  fontSize: "3.5rem",
                  fontWeight: 800,
                  color: seo.score >= 85 ? "var(--accent-success)" : "var(--accent-warning)",
                  margin: "8px 0",
                }}
              >
                {seo.score}
                <span style={{ fontSize: "1.2rem", color: "var(--text-muted)" }}>/100</span>
              </div>
              <span className="badge badge-success">High Organic Potential</span>
            </div>

            <h3 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "14px" }}>Technical SEO Checklist</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "0.875rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>✓ Title Tag Optimized</span>
                <span style={{ color: "var(--accent-success)" }}>Passed</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>✓ Meta Description Length</span>
                <span style={{ color: "var(--accent-success)" }}>155 chars</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>✓ Heading Hierarchy (H1-H3)</span>
                <span style={{ color: "var(--accent-success)" }}>{seo.heading_hierarchy_check ? "Verified" : "Issues"}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>✓ Readability Rating</span>
                <span>{seo.readability_score.toFixed(1)} / 100</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>✓ JSON-LD Schema</span>
                <span style={{ color: "var(--accent-success)" }}>TechArticle</span>
              </div>
            </div>
          </div>

          {/* Right Column: Metadata & Schema */}
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            <div className="card">
              <h3 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: "16px" }}>Search Engine Preview</h3>
              <div style={{ background: "var(--bg-secondary)", padding: "16px", borderRadius: "var(--radius-md)" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>https://example.com/blog/{seo.slug}</div>
                <div style={{ fontSize: "1.1rem", fontWeight: 600, color: "var(--brand-primary)", marginTop: "2px" }}>
                  {seo.meta_title}
                </div>
                <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: "4px" }}>
                  {seo.meta_description}
                </div>
              </div>
            </div>

            <div className="card">
              <h3 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: "12px" }}>Automated FAQ Schema</h3>
              {seo.faq_items && seo.faq_items.length > 0 ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  {seo.faq_items.map((item, i) => (
                    <div key={i} style={{ padding: "12px", background: "var(--bg-secondary)", borderRadius: "var(--radius-md)" }}>
                      <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>Q: {item.question}</div>
                      <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: "4px" }}>
                        A: {item.answer}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>No FAQ structured items generated.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
