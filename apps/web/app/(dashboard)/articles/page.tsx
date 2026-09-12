"use client";

import React, { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { Article, Project } from "@/lib/types";

function ArticlesListContent() {
  const searchParams = useSearchParams();
  const initialProjectId = searchParams.get("project_id") || "";

  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState(initialProjectId);
  const [articles, setArticles] = useState<Article[]>([]);
  const [filterStatus, setFilterStatus] = useState<string>("ALL");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getProjects().then((projs) => {
      setProjects(projs);
      if (projs.length > 0 && !selectedProjectId) {
        setSelectedProjectId(projs[0].id);
      }
    });
  }, [selectedProjectId]);

  useEffect(() => {
    if (selectedProjectId) {
      setLoading(true);
      api.getArticles(selectedProjectId)
        .then(setArticles)
        .catch(() => setArticles([]))
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [selectedProjectId]);

  const filteredArticles = articles.filter(
    (a) => filterStatus === "ALL" || a.status === filterStatus
  );

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "28px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.02em" }}>Articles Management</h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginTop: "4px" }}>
            Draft, review, optimize, and publish grounded blog articles.
          </p>
        </div>
        <Link href={`/articles/new?project_id=${selectedProjectId}`} className="btn btn-primary">
          + New Article Wizard
        </Link>
      </div>

      {/* Filter Bar */}
      <div style={{ display: "flex", gap: "16px", marginBottom: "24px", flexWrap: "wrap", alignItems: "center" }}>
        <div style={{ minWidth: "220px" }}>
          <select
            className="select"
            value={selectedProjectId}
            onChange={(e) => setSelectedProjectId(e.target.value)}
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                Project: {p.name}
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: "flex", gap: "6px" }}>
          {["ALL", "DRAFT", "IN_REVIEW", "APPROVED", "PUBLISHED"].map((st) => (
            <button
              key={st}
              onClick={() => setFilterStatus(st)}
              className="btn btn-secondary"
              style={{
                fontSize: "0.8rem",
                padding: "6px 12px",
                background: filterStatus === st ? "var(--brand-primary)" : "transparent",
                color: filterStatus === st ? "#fff" : "var(--text-secondary)",
              }}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Articles Table */}
      {loading ? (
        <div style={{ textAlign: "center", padding: "40px" }}>Loading articles...</div>
      ) : filteredArticles.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "48px 20px" }}>
          <div style={{ fontSize: "2.5rem", marginBottom: "10px" }}>✍️</div>
          <h3 style={{ fontSize: "1.15rem", fontWeight: 700 }}>No Articles Found</h3>
          <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: "4px" }}>
            Get started by creating your first article using the autonomous 11-agent wizard.
          </p>
          <Link href={`/articles/new?project_id=${selectedProjectId}`} className="btn btn-primary" style={{ marginTop: "16px" }}>
            Launch Article Wizard
          </Link>
        </div>
      ) : (
        <div className="card" style={{ padding: "0", overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
            <thead>
              <tr style={{ background: "var(--bg-secondary)", borderBottom: "1px solid var(--border-subtle)", textAlign: "left" }}>
                <th style={{ padding: "14px 20px", fontWeight: 600 }}>Title & Topic</th>
                <th style={{ padding: "14px 20px", fontWeight: 600 }}>Status</th>
                <th style={{ padding: "14px 20px", fontWeight: 600 }}>Version</th>
                <th style={{ padding: "14px 20px", fontWeight: 600 }}>Words</th>
                <th style={{ padding: "14px 20px", fontWeight: 600 }}>Engine</th>
                <th style={{ padding: "14px 20px", fontWeight: 600, textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredArticles.map((art) => (
                <tr key={art.id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                  <td style={{ padding: "14px 20px" }}>
                    <Link href={`/articles/${art.id}`} style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                      {art.title}
                    </Link>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "2px" }}>
                      Topic: {art.topic}
                    </div>
                  </td>
                  <td style={{ padding: "14px 20px" }}>
                    <span
                      className={`badge ${
                        art.status === "PUBLISHED"
                          ? "badge-success"
                          : art.status === "APPROVED"
                          ? "badge-info"
                          : "badge-warning"
                      }`}
                    >
                      {art.status}
                    </span>
                  </td>
                  <td style={{ padding: "14px 20px", color: "var(--text-muted)" }}>v{art.current_version}</td>
                  <td style={{ padding: "14px 20px" }}>{art.word_count}</td>
                  <td style={{ padding: "14px 20px", fontSize: "0.8rem", color: "var(--text-muted)" }}>
                    {art.generated_by_provider || "—"}
                  </td>
                  <td style={{ padding: "14px 20px", textAlign: "right" }}>
                    <Link href={`/articles/${art.id}`} className="btn btn-secondary" style={{ padding: "6px 12px", fontSize: "0.8rem" }}>
                      Workspace →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function ArticlesListPage() {
  return (
    <Suspense fallback={<div style={{ textAlign: "center", padding: "40px" }}>Loading Articles...</div>}>
      <ArticlesListContent />
    </Suspense>
  );
}
