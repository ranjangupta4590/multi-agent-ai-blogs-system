"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

export default function AdminPromptsPage() {
  const [prompts, setPrompts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPrompt, setSelectedPrompt] = useState<any | null>(null);
  const [systemPrompt, setSystemPrompt] = useState("");
  const [userTemplate, setUserTemplate] = useState("");
  const [publishing, setPublishing] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const loadPrompts = async () => {
    try {
      const data = await api.getPrompts();
      setPrompts(data);
      if (data.length > 0 && !selectedPrompt) {
        setSelectedPrompt(data[0]);
        setSystemPrompt(data[0].system_prompt);
        setUserTemplate(data[0].user_template);
      }
    } catch (err: any) {
      setFeedback("Failed to load prompts: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPrompts();
  }, []);

  const handleSelect = (p: any) => {
    setSelectedPrompt(p);
    setSystemPrompt(p.system_prompt);
    setUserTemplate(p.user_template);
    setFeedback(null);
  };

  const handlePublishNewVersion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPrompt) return;
    setPublishing(true);
    try {
      await api.createPromptVersion(selectedPrompt.id, systemPrompt, userTemplate);
      setFeedback(`New active version published for '${selectedPrompt.name}'!`);
      await loadPrompts();
    } catch (err: any) {
      setFeedback("Failed to publish version: " + err.message);
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "28px" }}>
        <div>
          <div style={{ fontSize: "0.8rem", color: "var(--brand-primary)", fontWeight: 700 }}>
            <Link href="/admin">← Back to Admin Console</Link>
          </div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.02em", marginTop: "4px" }}>
            Prompt Versioning & Governance
          </h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginTop: "4px" }}>
            All 11 agent prompts are strictly versioned. Create and publish new versions with full audit trails.
          </p>
        </div>
      </div>

      {feedback && (
        <div className="badge-info" style={{ padding: "10px 16px", borderRadius: "var(--radius-md)", marginBottom: "20px" }}>
          {feedback}
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: "center", padding: "40px" }}>Loading prompts...</div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: "24px" }}>
          {/* Prompt List */}
          <div className="card" style={{ padding: "16px" }}>
            <div style={{ fontSize: "0.8rem", textTransform: "uppercase", color: "var(--text-muted)", fontWeight: 700, marginBottom: "12px" }}>
              Agent Prompts
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              {prompts.map((p) => {
                const isSelected = selectedPrompt?.id === p.id;
                return (
                  <button
                    key={p.id}
                    onClick={() => handleSelect(p)}
                    style={{
                      padding: "10px 14px",
                      borderRadius: "var(--radius-md)",
                      textAlign: "left",
                      background: isSelected ? "var(--brand-glow)" : "transparent",
                      border: isSelected ? "1px solid var(--brand-primary)" : "1px solid transparent",
                      color: isSelected ? "var(--brand-primary)" : "var(--text-primary)",
                      fontWeight: isSelected ? 600 : 500,
                      cursor: "pointer",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <div>
                      <div style={{ fontSize: "0.875rem" }}>{p.agent_name}</div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>v{p.current_version} Active</div>
                    </div>
                    <span className="badge badge-info" style={{ fontSize: "0.7rem" }}>
                      {p.versions_count} v
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Prompt Editor & Version Publisher */}
          {selectedPrompt && (
            <div className="card" style={{ padding: "28px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
                <div>
                  <h2 style={{ fontSize: "1.25rem", fontWeight: 700 }}>
                    {selectedPrompt.agent_name} Prompt
                  </h2>
                  <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: "2px" }}>
                    Currently at <strong>Version {selectedPrompt.current_version}</strong> • {selectedPrompt.description}
                  </p>
                </div>
              </div>

              <form onSubmit={handlePublishNewVersion} style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "6px" }}>
                    System Prompt Instructions
                  </label>
                  <textarea
                    className="textarea"
                    rows={6}
                    style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem" }}
                    value={systemPrompt}
                    onChange={(e) => setSystemPrompt(e.target.value)}
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "6px" }}>
                    User Prompt Template
                  </label>
                  <textarea
                    className="textarea"
                    rows={4}
                    style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem" }}
                    value={userTemplate}
                    onChange={(e) => setUserTemplate(e.target.value)}
                  />
                </div>

                <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                  <button
                    type="submit"
                    disabled={publishing}
                    className="btn btn-primary"
                  >
                    {publishing ? "Publishing..." : `Publish New Version (${selectedPrompt.current_version + 1})`}
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
