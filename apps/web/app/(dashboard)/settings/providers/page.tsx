"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { AIProvider } from "@/lib/types";

export default function ProvidersSettingsPage() {
  const [providers, setProviders] = useState<AIProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeModalProvider, setActiveModalProvider] = useState<string | null>(null);
  const [apiKeys, setApiKeys] = useState<string[]>([""]);
  const [selectedModel, setSelectedModel] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [healthStatus, setHealthStatus] = useState<Record<string, string>>({});
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const loadProviders = async () => {
    try {
      const data = await api.getProviders();
      setProviders(data);
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message || "Failed to load providers" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProviders();
  }, []);

  const handleSetActive = async (providerName: string, modelName?: string) => {
    try {
      await api.setActiveProvider(providerName, modelName);
      setFeedback({ type: "success", text: `Switched active AI engine to ${providerName}. All 11 agents now use this provider.` });
      await loadProviders();
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message || "Failed to set active provider" });
    }
  };

  const handleAddKey = () => {
    setApiKeys((prev) => [...prev, ""]);
  };

  const handleRemoveKey = (index: number) => {
    setApiKeys((prev) => prev.filter((_, i) => i !== index));
  };

  const handleKeyChange = (index: number, value: string) => {
    setApiKeys((prev) => {
      const copy = [...prev];
      copy[index] = value;
      return copy;
    });
  };

  const handleConfigureSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeModalProvider) return;
    setSubmitting(true);
    try {
      const validKeys = apiKeys.map((k) => k.trim()).filter(Boolean);
      const keyPayload = validKeys.length > 0 ? validKeys.join(",") : undefined;
      await api.configureProvider(activeModalProvider, keyPayload, selectedModel || undefined);
      const pooledInfo = validKeys.length > 1 ? ` with ${validKeys.length} pooled keys` : "";
      setFeedback({ type: "success", text: `${activeModalProvider} credentials configured securely${pooledInfo}.` });
      setActiveModalProvider(null);
      setApiKeys([""]);
      await loadProviders();
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message || "Failed to save configuration" });
    } finally {
      setSubmitting(false);
    }
  };

  const handleHealthCheck = async (providerName: string) => {
    setHealthStatus((prev) => ({ ...prev, [providerName]: "Checking..." }));
    try {
      const res = await api.checkProviderHealth(providerName);
      setHealthStatus((prev) => ({
        ...prev,
        [providerName]: res.is_healthy ? `● Healthy (${res.latency_ms}ms)` : `○ ${res.message}`,
      }));
    } catch (err: any) {
      setHealthStatus((prev) => ({ ...prev, [providerName]: "Check failed" }));
    }
  };

  const activeProvider = providers.find((p) => p.is_active);

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: "28px" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.02em" }}>AI Engine & Provider Architecture</h1>
        <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginTop: "4px" }}>
          Centralized LLM Gateway settings. The entire platform operates autonomously with <strong>only ONE active provider</strong>.
        </p>
      </div>

      {/* Feedback banner */}
      {feedback && (
        <div
          className={feedback.type === "success" ? "badge-success" : "badge-danger"}
          style={{ padding: "12px 18px", borderRadius: "var(--radius-md)", marginBottom: "24px", fontSize: "0.875rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}
        >
          <span>{feedback.text}</span>
          <button onClick={() => setFeedback(null)} style={{ background: "transparent", border: "none", cursor: "pointer", color: "inherit", fontWeight: 700 }}>✕</button>
        </div>
      )}

      {/* Active Provider Callout */}
      <div
        className="glass-panel"
        style={{
          padding: "24px",
          marginBottom: "32px",
          borderLeft: "4px solid var(--brand-primary)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "16px",
        }}
      >
        <div>
          <div style={{ fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--brand-primary)", fontWeight: 700 }}>
            Current System-Wide AI Provider
          </div>
          <div style={{ fontSize: "1.35rem", fontWeight: 800, marginTop: "4px", display: "flex", alignItems: "center", gap: "10px" }}>
            {activeProvider ? (
              <>
                <span className="pulse-dot" />
                <span>{activeProvider.display_name}</span>
                <span className="badge badge-success" style={{ fontSize: "0.75rem" }}>Active & Injected</span>
              </>
            ) : (
              <>
                <span style={{ color: "var(--accent-warning)" }}>⚠️ No Provider Configured</span>
                <span className="badge badge-warning" style={{ fontSize: "0.75rem" }}>Action Required</span>
              </>
            )}
          </div>
          <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: "6px", maxWidth: "680px" }}>
            {activeProvider
              ? `All 11 autonomous agents (Research Planner, Researcher, Validator, Strategist, Outline, Writer, Fact Checker, SEO, Critic, Editor, Publisher) are currently executing through ${activeProvider.name}.`
              : "Configure and connect at least one AI provider below to start generating content. The rest of the application remains fully functional."}
          </p>
        </div>
      </div>

      {/* Provider Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "20px" }}>
        {providers.map((p) => {
          const isConnected = p.connection_status === "CONNECTED";
          const isActive = p.is_active;

          return (
            <div
              key={p.name}
              className="card"
              style={{
                border: isActive ? "2px solid var(--brand-primary)" : "1px solid var(--border-subtle)",
                boxShadow: isActive ? "0 0 20px var(--brand-glow)" : undefined,
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
              }}
            >
              <div>
                {/* Header row */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "14px" }}>
                  <h3 style={{ fontSize: "1.1rem", fontWeight: 700 }}>{p.name}</h3>
                  {isConnected ? (
                    <span className="badge badge-success">● Connected</span>
                  ) : (
                    <span className="badge" style={{ background: "var(--bg-secondary)", color: "var(--text-muted)" }}>
                      ○ Not Configured
                    </span>
                  )}
                </div>

                <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "16px" }}>
                  <div><strong>Credential:</strong> {isConnected ? "Configured securely" : "Not configured"}</div>
                  <div style={{ marginTop: "4px" }}><strong>Default Model:</strong> {p.default_model}</div>
                </div>

                {healthStatus[p.name] && (
                  <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: "14px", padding: "6px 10px", background: "var(--bg-secondary)", borderRadius: "var(--radius-sm)" }}>
                    Health: {healthStatus[p.name]}
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "16px" }}>
                {isConnected ? (
                  <>
                    {isActive ? (
                      <div className="btn btn-primary" style={{ cursor: "default", opacity: 0.9 }}>
                        ✓ Currently Active Engine
                      </div>
                    ) : (
                      <button
                        onClick={() => handleSetActive(p.name, p.default_model)}
                        className="btn btn-outline"
                      >
                        Set as Active AI Provider
                      </button>
                    )}
                    <div style={{ display: "flex", gap: "8px" }}>
                      <button
                        onClick={() => handleHealthCheck(p.name)}
                        className="btn btn-secondary"
                        style={{ flex: 1, fontSize: "0.75rem", padding: "6px" }}
                      >
                        Health Check
                      </button>
                      <button
                        onClick={() => {
                          setActiveModalProvider(p.name);
                          setSelectedModel(p.default_model);
                          setApiKeys([""]);
                        }}
                        className="btn btn-secondary"
                        style={{ flex: 1, fontSize: "0.75rem", padding: "6px" }}
                      >
                        Update Key
                      </button>
                    </div>
                  </>
                ) : (
                  <button
                    onClick={() => {
                      setActiveModalProvider(p.name);
                      setSelectedModel(p.default_model);
                      setApiKeys([""]);
                    }}
                    className="btn btn-primary"
                  >
                    + Configure {p.name}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Secret Configuration Modal */}
      {activeModalProvider && (
        <div className="modal-overlay" onClick={() => setActiveModalProvider(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div style={{ padding: "24px", borderBottom: "1px solid var(--border-subtle)" }}>
              <h2 style={{ fontSize: "1.25rem", fontWeight: 700 }}>
                Configure {activeModalProvider}
              </h2>
              <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: "4px" }}>
                Stored API keys are never displayed again. Leave blank to keep current server-side credentials.
              </p>
            </div>

            <form onSubmit={handleConfigureSubmit} style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "16px" }}>
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                  <label style={{ fontSize: "0.8rem", fontWeight: 600 }}>
                    API Key{apiKeys.length > 1 ? `s (${apiKeys.length})` : " (optional)"}
                  </label>
                  <button
                    type="button"
                    onClick={handleAddKey}
                    className="btn btn-secondary"
                    style={{ fontSize: "0.75rem", padding: "4px 10px", display: "inline-flex", alignItems: "center", gap: "5px" }}
                  >
                    <span>+</span> Add another key
                  </button>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {apiKeys.map((k, idx) => (
                    <div key={idx} style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                      <input
                        type="password"
                        className="input"
                        placeholder={
                          apiKeys.length === 1
                            ? `Enter ${activeModalProvider} API Key`
                            : `API Key #${idx + 1}`
                        }
                        value={k}
                        onChange={(e) => handleKeyChange(idx, e.target.value)}
                        style={{ flex: 1 }}
                      />
                      {apiKeys.length > 1 && (
                        <button
                          type="button"
                          onClick={() => handleRemoveKey(idx)}
                          className="btn btn-secondary"
                          title="Remove this key"
                          style={{
                            padding: "8px 12px",
                            color: "var(--accent-danger)",
                            borderColor: "var(--border-subtle)",
                            fontSize: "0.9rem",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                          }}
                        >
                          🗑️
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "6px" }}>
                  Default Model
                </label>
                <input
                  type="text"
                  className="input"
                  placeholder="e.g. gpt-4o, claude-3-5-sonnet-20241022"
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "12px" }}>
                <button
                  type="button"
                  onClick={() => setActiveModalProvider(null)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="btn btn-primary"
                >
                  {submitting ? "Validating & Saving..." : "Save Credential"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
