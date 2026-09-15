"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Link from "next/link";
import { api } from "@/lib/api";
import { Article, ArticleVersion, Claim, SEOAnalysis, Source } from "@/lib/types";

export default function ArticleEditorWorkspacePage() {
  const params = useParams();
  const router = useRouter();
  const articleId = params?.id as string;

  const [article, setArticle] = useState<Article | null>(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [sources, setSources] = useState<Source[]>([]);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [seo, setSeo] = useState<SEOAnalysis | null>(null);
  const [versions, setVersions] = useState<ArticleVersion[]>([]);
  const [activeTab, setActiveTab] = useState<"sources" | "claims" | "seo" | "critic" | "versions">("sources");
  const [contentMode, setContentMode] = useState<"markdown" | "preview">("markdown");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);


  const loadAll = async () => {
    try {
      const [art, srcList, claimList, seoData, vList] = await Promise.all([
        api.getArticle(articleId),
        api.getSources(articleId).catch(() => []),
        api.getClaims(articleId).catch(() => []),
        api.getSEO(articleId).catch(() => null),
        api.getArticleVersions(articleId).catch(() => []),
      ]);
      setArticle(art);
      setTitle(art.title);
      setContent(art.content);
      setSources(srcList);
      setClaims(claimList);
      setSeo(seoData);
      setVersions(vList);
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message || "Failed to load article workspace" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (articleId) {
      loadAll();
    }
  }, [articleId]);

  const handleSaveManual = async () => {
    setSaving(true);
    setFeedback(null);
    try {
      const updated = await api.updateArticle(articleId, {
        title,
        content,
        change_summary: "Manual editorial update in workspace",
      });
      setArticle(updated);
      setFeedback({ type: "success", text: `Saved version ${updated.current_version} successfully.` });
      const vList = await api.getArticleVersions(articleId);
      setVersions(vList);
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message || "Failed to save article" });
    } finally {
      setSaving(false);
    }
  };

  const handleApproveHumanReview = async () => {
    setSaving(true);
    try {
      const updated = await api.updateArticle(articleId, {
        status: "APPROVED",
        change_summary: "Approved by human editor",
      });
      setArticle(updated);
      setFeedback({ type: "success", text: "Article approved. You can now publish it to the public BlogPilot home page." });
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message || "Failed to approve article" });
    } finally {
      setSaving(false);
    }
  };

  const handleRestoreVersion = async (vNum: number) => {
    if (!confirm(`Restore content from version ${vNum}?`)) return;
    setSaving(true);
    try {
      const restored = await api.restoreVersion(articleId, vNum);
      setArticle(restored);
      setTitle(restored.title);
      setContent(restored.content);
      setFeedback({ type: "success", text: `Restored version ${vNum} as new active version ${restored.current_version}.` });
      const vList = await api.getArticleVersions(articleId);
      setVersions(vList);
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message || "Failed to restore version" });
    } finally {
      setSaving(false);
    }
  };

  const handlePublishPublic = async () => {
    if (!confirm("Publish this approved article to the public BlogPilot home page?")) return;
    setSaving(true);
    try {
      const updated = await api.updateArticle(articleId, {
        status: "PUBLISHED",
        change_summary: "Published publicly on BlogPilot",
      });
      setArticle(updated);
      setFeedback({ type: "success", text: "Article is now public on the BlogPilot home page." });
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message || "Failed to publish article" });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div style={{ textAlign: "center", padding: "60px" }}>Loading Article Workspace...</div>;
  }

  if (!article) {
    return (
      <div className="card" style={{ textAlign: "center", padding: "40px" }}>
        <h3>Article Not Found</h3>
        <Link href="/articles" className="btn btn-primary" style={{ marginTop: "12px" }}>
          Back to Articles
        </Link>
      </div>
    );
  }

  const criticEval = article.critic_evaluation || {};

  return (
    <div>
      {/* Workspace Top Bar */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "18px", flexWrap: "wrap", gap: "12px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <Link href="/articles" className="btn btn-secondary" style={{ padding: "6px 10px", fontSize: "0.8rem" }}>
            ← Articles
          </Link>
          <span className={`badge ${article.status === "PUBLISHED" ? "badge-success" : article.status === "APPROVED" ? "badge-info" : "badge-warning"}`}>
            {article.status}
          </span>
          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
            Version {article.current_version} • {article.word_count} words • ~{article.estimated_reading_time} min read
          </span>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <button onClick={handleSaveManual} disabled={saving} className="btn btn-secondary">
            {saving ? "Saving..." : "Save Draft"}
          </button>

          {article.status === "IN_REVIEW" && (
            <button onClick={handleApproveHumanReview} disabled={saving} className="btn btn-primary">
              ✓ Human Approve
            </button>
          )}

          {article.status === "APPROVED" && (
            <button onClick={handlePublishPublic} disabled={saving} className="btn btn-primary" style={{ background: "var(--brand-gradient)" }}>
              🌐 Publish to Public Blog
            </button>
          )}
        </div>
      </div>

      {feedback && (
        <div
          className={feedback.type === "success" ? "badge-success" : "badge-danger"}
          style={{ padding: "10px 16px", borderRadius: "var(--radius-md)", marginBottom: "18px", fontSize: "0.85rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}
        >
          <span>{feedback.text}</span>
          <button onClick={() => setFeedback(null)} style={{ background: "transparent", border: "none", cursor: "pointer", color: "inherit" }}>✕</button>
        </div>
      )}

      {/* Split-Screen Main Layout */}
      <div className="article-workspace-grid">
        {/* Left Pane: Rich Text / Markdown Editor */}
        <div className="card workspace-editor-pane" style={{ padding: "28px" }}>
          <div style={{ marginBottom: "16px" }}>
            <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", color: "var(--text-muted)", marginBottom: "4px" }}>
              Article Title
            </label>
            <input
              type="text"
              className="input"
              style={{ fontSize: "1.25rem", fontWeight: 700 }}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>

          <div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
              <span style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", color: "var(--text-muted)" }}>Content</span>
              <div style={{ display: "flex", gap: "4px" }}>
                <button type="button" onClick={() => setContentMode("markdown")} className="btn btn-secondary" style={{ padding: "5px 10px", fontSize: "0.78rem", background: contentMode === "markdown" ? "var(--brand-primary)" : "transparent", color: contentMode === "markdown" ? "#fff" : "var(--text-secondary)" }}>Markdown</button>
                <button type="button" onClick={() => setContentMode("preview")} className="btn btn-secondary" style={{ padding: "5px 10px", fontSize: "0.78rem", background: contentMode === "preview" ? "var(--brand-primary)" : "transparent", color: contentMode === "preview" ? "#fff" : "var(--text-secondary)" }}>Preview</button>
              </div>
            </div>
            {contentMode === "markdown" ? (
              <textarea className="textarea" style={{ fontFamily: "var(--font-mono)", fontSize: "0.9rem", lineHeight: 1.6, minHeight: "560px", resize: "vertical" }} value={content} onChange={(e) => setContent(e.target.value)} />
            ) : (
              <div className="prose markdown-preview">
                {content.trim() ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown> : <p style={{ color: "var(--text-muted)" }}>Nothing to preview yet.</p>}
              </div>
            )}
          </div>
        </div>

        {/* Right Pane: AI Workspace Drawer */}
        <div className="card workspace-insights-pane" style={{ padding: "20px" }}>
          {/* Tabs header */}
          <div style={{ display: "flex", gap: "6px", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "12px", marginBottom: "16px", overflowX: "auto" }}>
            <button
              onClick={() => setActiveTab("sources")}
              className="btn btn-secondary"
              style={{
                padding: "6px 12px",
                fontSize: "0.8rem",
                background: activeTab === "sources" ? "var(--brand-primary)" : "transparent",
                color: activeTab === "sources" ? "#fff" : "var(--text-secondary)",
              }}
            >
              Sources ({sources.length})
            </button>
            <button
              onClick={() => setActiveTab("claims")}
              className="btn btn-secondary"
              style={{
                padding: "6px 12px",
                fontSize: "0.8rem",
                background: activeTab === "claims" ? "var(--brand-primary)" : "transparent",
                color: activeTab === "claims" ? "#fff" : "var(--text-secondary)",
              }}
            >
              Claims ({claims.length})
            </button>
            <button
              onClick={() => setActiveTab("seo")}
              className="btn btn-secondary"
              style={{
                padding: "6px 12px",
                fontSize: "0.8rem",
                background: activeTab === "seo" ? "var(--brand-primary)" : "transparent",
                color: activeTab === "seo" ? "#fff" : "var(--text-secondary)",
              }}
            >
              SEO Score
            </button>
            <button
              onClick={() => setActiveTab("critic")}
              className="btn btn-secondary"
              style={{
                padding: "6px 12px",
                fontSize: "0.8rem",
                background: activeTab === "critic" ? "var(--brand-primary)" : "transparent",
                color: activeTab === "critic" ? "#fff" : "var(--text-secondary)",
              }}
            >
              Critique
            </button>
            <button
              onClick={() => setActiveTab("versions")}
              className="btn btn-secondary"
              style={{
                padding: "6px 12px",
                fontSize: "0.8rem",
                background: activeTab === "versions" ? "var(--brand-primary)" : "transparent",
                color: activeTab === "versions" ? "#fff" : "var(--text-secondary)",
              }}
            >
              History ({versions.length})
            </button>
          </div>

          {/* Tab 1: Sources */}
          {activeTab === "sources" && (
            <div>
              <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "12px" }}>
                Curated authoritative evidence collected during autonomous research:
              </div>
              {sources.length === 0 ? (
                <div style={{ textAlign: "center", padding: "24px", color: "var(--text-muted)", fontSize: "0.85rem" }}>
                  No sources collected yet.
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  {sources.map((s, idx) => (
                    <div
                      key={s.id || idx}
                      style={{
                        padding: "12px",
                        background: "var(--bg-secondary)",
                        borderRadius: "var(--radius-md)",
                        fontSize: "0.85rem",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                        <span className="badge badge-info" style={{ fontSize: "0.7rem" }}>{s.source_type}</span>
                        <span style={{ fontSize: "0.75rem", color: "var(--accent-success)", fontWeight: 600 }}>
                          {(s.credibility_score * 100).toFixed(0)}% Trust
                        </span>
                      </div>
                      <a href={s.url} target="_blank" rel="noopener noreferrer" style={{ fontWeight: 600, color: "var(--brand-primary)" }}>
                        {s.title}
                      </a>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "2px" }}>{s.domain}</div>
                      {s.snippet && (
                        <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "6px" }}>{s.snippet}</div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Tab 2: Grounded Claims */}
          {activeTab === "claims" && (
            <div>
              <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "12px" }}>
                Verifiable factual assertions audited by the Fact Checker agent:
              </div>
              {claims.length === 0 ? (
                <div style={{ textAlign: "center", padding: "24px", color: "var(--text-muted)", fontSize: "0.85rem" }}>
                  No claims extracted yet.
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  {claims.map((c, idx) => {
                    const isVerified = c.status === "VERIFIED";
                    const isPartial = c.status === "PARTIALLY_VERIFIED";
                    return (
                      <div
                        key={c.id || idx}
                        style={{
                          padding: "12px",
                          background: "var(--bg-secondary)",
                          borderRadius: "var(--radius-md)",
                          fontSize: "0.85rem",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                          <span className={`badge ${isVerified ? "badge-success" : isPartial ? "badge-warning" : "badge-danger"}`} style={{ fontSize: "0.7rem" }}>
                            {c.status}
                          </span>
                          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                            Confidence: {(c.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div style={{ fontWeight: 500 }}>"{c.claim_text}"</div>
                        {c.notes && (
                          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "4px" }}>
                            Note: {c.notes}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Tab 3: SEO Analysis */}
          {activeTab === "seo" && (
            <div>
              {seo ? (
                <div>
                  {/* Gauge Card */}
                  <div
                    style={{
                      background: "var(--bg-secondary)",
                      padding: "16px",
                      borderRadius: "var(--radius-md)",
                      textAlign: "center",
                      marginBottom: "16px",
                    }}
                  >
                    <div style={{ fontSize: "0.8rem", textTransform: "uppercase", color: "var(--text-muted)", fontWeight: 700 }}>
                      SEO Visibility Score
                    </div>
                    <div style={{ fontSize: "2.5rem", fontWeight: 800, color: seo.score >= 80 ? "var(--accent-success)" : "var(--accent-warning)", margin: "4px 0" }}>
                      {seo.score}/100
                    </div>
                    <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                      Readability: {seo.readability_score?.toFixed(1) || 75.0} • Heading Structure: {seo.heading_hierarchy_check ? "✓ Valid" : "⚠ Issues"}
                    </div>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "0.85rem" }}>
                    <div>
                      <strong>Meta Title:</strong> {seo.meta_title}
                    </div>
                    <div>
                      <strong>Meta Description:</strong> {seo.meta_description}
                    </div>
                    <div>
                      <strong>Slug:</strong> /{seo.slug}
                    </div>
                    <div>
                      <strong>Focus Keywords:</strong> {seo.focus_keywords?.join(", ") || "Auto"}
                    </div>
                  </div>
                </div>
              ) : (
                <div style={{ textAlign: "center", padding: "24px", color: "var(--text-muted)", fontSize: "0.85rem" }}>
                  SEO audit pending or not generated yet.
                </div>
              )}
            </div>
          )}

          {/* Tab 4: Critique */}
          {activeTab === "critic" && (
            <div>
              <div style={{ background: "var(--bg-secondary)", padding: "16px", borderRadius: "var(--radius-md)", marginBottom: "16px" }}>
                <div style={{ fontSize: "0.8rem", textTransform: "uppercase", color: "var(--text-muted)", fontWeight: 700 }}>
                  Critic Quality Rating
                </div>
                <div style={{ fontSize: "2rem", fontWeight: 800, color: "var(--brand-primary)", marginTop: "4px" }}>
                  {criticEval.score !== undefined ? `${criticEval.score}/10.0` : "Pending"}
                </div>
              </div>

              {criticEval.issues && criticEval.issues.length > 0 && (
                <div>
                  <h4 style={{ fontSize: "0.85rem", fontWeight: 700, marginBottom: "8px" }}>Editorial Improvement Items</h4>
                  <ul style={{ paddingLeft: "20px", fontSize: "0.85rem", display: "flex", flexDirection: "column", gap: "4px", color: "var(--text-secondary)" }}>
                    {criticEval.issues.map((iss: string, i: number) => (
                      <li key={i}>{iss}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Tab 5: Version History */}
          {activeTab === "versions" && (
            <div>
              <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "12px" }}>
                Snapshot history. Restore any previous milestone safely:
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {versions.map((v) => (
                  <div
                    key={v.id}
                    style={{
                      padding: "12px",
                      background: "var(--bg-secondary)",
                      borderRadius: "var(--radius-md)",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600, fontSize: "0.85rem" }}>
                        Version {v.version_number} {v.version_number === article.current_version && "(Active)"}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                        {v.change_summary || "Snapshot"} • by {v.created_by}
                      </div>
                    </div>
                    {v.version_number !== article.current_version && (
                      <button
                        onClick={() => handleRestoreVersion(v.version_number)}
                        className="btn btn-secondary"
                        style={{ padding: "4px 8px", fontSize: "0.75rem" }}
                      >
                        Restore
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

    </div>
  );
}
