"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Article, Claim, Project, Source } from "@/lib/types";

export default function SourcesGroundingPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [articles, setArticles] = useState<Article[]>([]);
  const [selectedArticleId, setSelectedArticleId] = useState("");
  const [sources, setSources] = useState<Source[]>([]);
  const [claims, setClaims] = useState<Claim[]>([]);
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
      Promise.all([
        api.getSources(selectedArticleId).catch(() => []),
        api.getClaims(selectedArticleId).catch(() => []),
      ])
        .then(([s, c]) => {
          setSources(s);
          setClaims(c);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [selectedArticleId]);

  return (
    <div>
      <div style={{ marginBottom: "28px" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.02em" }}>Sources & Grounding Verification</h1>
        <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginTop: "4px" }}>
          Inspect external evidence citations and audited factual claims for every generated article.
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
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        <div style={{ minWidth: "280px" }}>
          <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: "4px" }}>
            SELECT ARTICLE
          </label>
          <select className="select" value={selectedArticleId} onChange={(e) => setSelectedArticleId(e.target.value)}>
            {articles.map((a) => (
              <option key={a.id} value={a.id}>
                {a.title}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: "center", padding: "40px" }}>Loading grounding data...</div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
          {/* Sources Explorer */}
          <div className="card">
            <h2 style={{ fontSize: "1.15rem", fontWeight: 700, marginBottom: "16px" }}>
              Authoritative Sources ({sources.length})
            </h2>
            {sources.length === 0 ? (
              <div style={{ textAlign: "center", padding: "30px", color: "var(--text-muted)" }}>
                No research sources found for this article.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {sources.map((s) => (
                  <div key={s.id} style={{ padding: "14px", background: "var(--bg-secondary)", borderRadius: "var(--radius-md)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                      <span className="badge badge-info">{s.source_type}</span>
                      <span style={{ fontSize: "0.8rem", color: "var(--accent-success)", fontWeight: 700 }}>
                        {(s.credibility_score * 100).toFixed(0)}% Trust Score
                      </span>
                    </div>
                    <div style={{ fontWeight: 600, fontSize: "0.95rem" }}>{s.title}</div>
                    <a href={s.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: "0.8rem", color: "var(--brand-primary)", wordBreak: "break-all" }}>
                      {s.url}
                    </a>
                    {s.snippet && (
                      <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "6px" }}>
                        {s.snippet}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Claims Verification */}
          <div className="card">
            <h2 style={{ fontSize: "1.15rem", fontWeight: 700, marginBottom: "16px" }}>
              Audited Claims ({claims.length})
            </h2>
            {claims.length === 0 ? (
              <div style={{ textAlign: "center", padding: "30px", color: "var(--text-muted)" }}>
                No claims verified yet for this article.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {claims.map((c) => (
                  <div key={c.id} style={{ padding: "14px", background: "var(--bg-secondary)", borderRadius: "var(--radius-md)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                      <span
                        className={`badge ${
                          c.status === "VERIFIED"
                            ? "badge-success"
                            : c.status === "PARTIALLY_VERIFIED"
                            ? "badge-warning"
                            : "badge-danger"
                        }`}
                      >
                        {c.status}
                      </span>
                      <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                        Confidence: {(c.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div style={{ fontWeight: 500, fontSize: "0.9rem" }}>"{c.claim_text}"</div>
                    {c.notes && (
                      <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "6px" }}>
                        Audit Note: {c.notes}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
