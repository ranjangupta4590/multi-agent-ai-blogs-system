"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Project } from "@/lib/types";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [name, setName] = useState("");
  const [brandVoice, setBrandVoice] = useState("Authoritative, technical, highly engaging");
  const [targetAudience, setTargetAudience] = useState("Enterprise software engineers and CTOs");
  const [industry, setIndustry] = useState("Technology & Cloud");
  const [tone, setTone] = useState("Professional");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadProjects = async () => {
    try {
      const data = await api.getProjects();
      setProjects(data);
    } catch (err: any) {
      setError(err.message || "Failed to load projects");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.createProject({
        name,
        brand_voice: brandVoice,
        target_audience: targetAudience,
        industry,
        tone,
      });
      setShowModal(false);
      setName("");
      await loadProjects();
    } catch (err: any) {
      setError(err.message || "Failed to create project");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "28px" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.02em" }}>Projects & Brands</h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginTop: "4px" }}>
            Each project encapsulates distinct brand voice, target audience, and editorial guidelines.
          </p>
        </div>
        <button onClick={() => setShowModal(true)} className="btn btn-primary">
          + New Project
        </button>
      </div>

      {error && (
        <div className="badge-danger" style={{ padding: "12px", borderRadius: "var(--radius-md)", marginBottom: "20px" }}>
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: "center", padding: "40px" }}>Loading projects...</div>
      ) : projects.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "48px 24px" }}>
          <div style={{ fontSize: "2.5rem", marginBottom: "12px" }}>📁</div>
          <h3 style={{ fontSize: "1.2rem", fontWeight: 700 }}>No Projects Configured</h3>
          <p style={{ color: "var(--text-muted)", fontSize: "0.875rem", marginTop: "4px", maxWidth: "450px", margin: "4px auto 20px" }}>
            Projects organize your blog publication verticals. Create your first project to begin drafting articles.
          </p>
          <button onClick={() => setShowModal(true)} className="btn btn-primary">
            Create First Project
          </button>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "20px" }}>
          {projects.map((proj) => (
            <div key={proj.id} className="card" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
                  <h3 style={{ fontSize: "1.2rem", fontWeight: 700 }}>{proj.name}</h3>
                  <span className="badge badge-info">{proj.industry || "General"}</span>
                </div>
                <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: "12px" }}>
                  {proj.description || "Active publishing vertical"}
                </p>

                <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", display: "flex", flexDirection: "column", gap: "4px" }}>
                  <div><strong>Audience:</strong> {proj.target_audience}</div>
                  <div><strong>Brand Voice:</strong> {proj.brand_voice}</div>
                  <div><strong>Tone:</strong> {proj.tone}</div>
                </div>
              </div>

              <div style={{ marginTop: "20px", display: "flex", gap: "10px" }}>
                <Link
                  href={`/articles?project_id=${proj.id}`}
                  className="btn btn-secondary"
                  style={{ flex: 1, textAlign: "center" }}
                >
                  View Articles
                </Link>
                <Link
                  href={`/articles/new?project_id=${proj.id}`}
                  className="btn btn-primary"
                  style={{ flex: 1, textAlign: "center" }}
                >
                  + Draft Article
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* New Project Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div style={{ padding: "24px", borderBottom: "1px solid var(--border-subtle)" }}>
              <h2 style={{ fontSize: "1.25rem", fontWeight: 700 }}>Create New Project</h2>
              <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: "4px" }}>
                Configure the brand profile that AI agents will adhere to.
              </p>
            </div>

            <form onSubmit={handleCreate} style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "16px" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "6px" }}>
                  Project Name
                </label>
                <input
                  type="text"
                  required
                  className="input"
                  placeholder="e.g. Cloud Security Insights"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "6px" }}>
                  Target Audience
                </label>
                <input
                  type="text"
                  className="input"
                  value={targetAudience}
                  onChange={(e) => setTargetAudience(e.target.value)}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "6px" }}>
                  Brand Voice Guidelines
                </label>
                <input
                  type="text"
                  className="input"
                  value={brandVoice}
                  onChange={(e) => setBrandVoice(e.target.value)}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "6px" }}>
                    Industry
                  </label>
                  <input
                    type="text"
                    className="input"
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "6px" }}>
                    Tone
                  </label>
                  <input
                    type="text"
                    className="input"
                    value={tone}
                    onChange={(e) => setTone(e.target.value)}
                  />
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "12px" }}>
                <button type="button" onClick={() => setShowModal(false)} className="btn btn-secondary">
                  Cancel
                </button>
                <button type="submit" disabled={submitting} className="btn btn-primary">
                  {submitting ? "Creating..." : "Create Project"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
