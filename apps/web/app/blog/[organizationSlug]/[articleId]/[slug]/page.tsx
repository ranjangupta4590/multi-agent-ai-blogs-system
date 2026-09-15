"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type PublicArticle = {
  organization_name: string;
  title: string;
  summary: string | null;
  content: string;
  estimated_reading_time: number;
  word_count: number;
  updated_at: string;
};

type PublicComment = {
  id: string;
  article_id: string;
  author_id: string;
  author_name: string;
  content: string;
  created_at: string;
  updated_at: string;
};

type CurrentUser = { id: string; full_name: string; role: string };

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

function SafeArticleContent({ content }: { content: string }) {
  return <div className="prose public-article-prose"><ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown></div>;
}

export default function PublicArticlePage() {
  const params = useParams();
  const organizationSlug = params.organizationSlug as string;
  const articleId = params.articleId as string;
  const slug = params.slug as string;
  const [article, setArticle] = useState<PublicArticle | null>(null);
  const [comments, setComments] = useState<PublicComment[]>([]);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [commentText, setCommentText] = useState("");
  const [editingCommentId, setEditingCommentId] = useState<string | null>(null);
  const [commentBusy, setCommentBusy] = useState(false);
  const [commentError, setCommentError] = useState("");
  const [error, setError] = useState("");

  const commentUrl = `${API_BASE}/public/articles/${encodeURIComponent(articleId)}/comments`;
  const authHeaders = (): Record<string, string> => {
    const token = window.localStorage.getItem("token");
    return token ? { "Content-Type": "application/json", Authorization: `Bearer ${token}` } : { "Content-Type": "application/json" };
  };

  const loadComments = async () => {
    if (!articleId) return;
    const response = await fetch(commentUrl);
    if (response.ok) setComments(await response.json());
  };

  useEffect(() => {
    if (!organizationSlug || !articleId || !slug) return;
    fetch(`${API_BASE}/public/organizations/${encodeURIComponent(organizationSlug)}/articles/${encodeURIComponent(articleId)}/${encodeURIComponent(slug)}`)
      .then(async (response) => {
        if (!response.ok) throw new Error("This article is unavailable or has not been published.");
        return response.json();
      })
      .then(setArticle)
      .catch((err) => setError(err.message || "Unable to load article."));
  }, [organizationSlug, articleId, slug]);

  useEffect(() => {
    if (!articleId) return;
    loadComments().catch(() => setCommentError("Comments could not be loaded."));
    const token = window.localStorage.getItem("token");
    if (token) {
      fetch(`${API_BASE}/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
        .then((response) => response.ok ? response.json() : null)
        .then(setCurrentUser)
        .catch(() => setCurrentUser(null));
    }
  }, [articleId]);

  const canModerate = (comment: PublicComment) => Boolean(currentUser && (currentUser.id === comment.author_id || ["SUPER_ADMIN", "ADMIN"].includes(currentUser.role)));

  const submitComment = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!commentText.trim()) return;
    setCommentBusy(true);
    setCommentError("");
    try {
      const endpoint = editingCommentId ? `${commentUrl}/${editingCommentId}` : commentUrl;
      const response = await fetch(endpoint, { method: editingCommentId ? "PUT" : "POST", headers: authHeaders(), body: JSON.stringify({ content: commentText }) });
      const payload = await response.json().catch(() => null);
      if (!response.ok) throw new Error(payload?.detail || "Unable to save your comment.");
      setComments((previous) => editingCommentId ? previous.map((comment) => comment.id === editingCommentId ? payload : comment) : [...previous, payload]);
      setCommentText("");
      setEditingCommentId(null);
    } catch (err: any) {
      setCommentError(err.message || "Unable to save your comment.");
    } finally {
      setCommentBusy(false);
    }
  };

  const deleteComment = async (commentId: string) => {
    if (!confirm("Delete this comment?")) return;
    setCommentBusy(true);
    setCommentError("");
    try {
      const response = await fetch(`${commentUrl}/${commentId}`, { method: "DELETE", headers: authHeaders() });
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail || "Unable to delete comment.");
      }
      setComments((previous) => previous.filter((comment) => comment.id !== commentId));
    } catch (err: any) {
      setCommentError(err.message || "Unable to delete comment.");
    } finally {
      setCommentBusy(false);
    }
  };

  if (error) return <main style={{ maxWidth: "760px", margin: "0 auto", padding: "80px 24px" }}><Link href="/">← All blogs</Link><h1>Article unavailable</h1><p>{error}</p></main>;
  if (!article) return <main style={{ maxWidth: "760px", margin: "0 auto", padding: "80px 24px", color: "var(--text-muted)" }}>Loading article…</main>;

  return (
    <main style={{ maxWidth: "800px", margin: "0 auto", padding: "42px 24px 90px" }}>
      <Link href="/" style={{ color: "var(--brand-primary)", fontWeight: 700 }}>← All blogs</Link>
      <article style={{ marginTop: "30px" }}>
        <div style={{ color: "var(--brand-primary)", fontWeight: 800, fontSize: "0.78rem", letterSpacing: "0.08em", textTransform: "uppercase" }}>{article.organization_name}</div>
        <h1 style={{ fontSize: "clamp(2.25rem, 6vw, 4rem)", letterSpacing: "-0.05em", lineHeight: 1.05, margin: "14px 0" }}>{article.title}</h1>
        {article.summary && <p style={{ fontSize: "1.18rem", lineHeight: 1.7, color: "var(--text-secondary)" }}>{article.summary}</p>}
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "38px" }}>{article.estimated_reading_time || 1} min read · {article.word_count} words · Updated {new Date(article.updated_at).toLocaleDateString()}</p>
        <SafeArticleContent content={article.content} />
      </article>

      <section className="public-comments" aria-labelledby="feedback-heading">
        <h2 id="feedback-heading">Reader feedback <span>({comments.length})</span></h2>
        {currentUser ? (
          <form onSubmit={submitComment} className="comment-form">
            <label htmlFor="comment">{editingCommentId ? "Edit your comment" : "Share your thoughts"}</label>
            <textarea id="comment" value={commentText} onChange={(event) => setCommentText(event.target.value)} maxLength={2000} placeholder="Write a respectful comment…" required />
            <div className="comment-form-actions">
              {editingCommentId && <button type="button" className="btn btn-secondary" onClick={() => { setEditingCommentId(null); setCommentText(""); }}>Cancel</button>}
              <button type="submit" className="btn btn-primary" disabled={commentBusy}>{commentBusy ? "Saving…" : editingCommentId ? "Update comment" : "Post comment"}</button>
            </div>
          </form>
        ) : (
          <p className="comment-signin">Want to leave feedback? <Link href="/login">Sign in</Link> or <Link href="/register">create an account</Link>.</p>
        )}
        {commentError && <p className="comment-error">{commentError}</p>}
        <div className="comment-list">
          {comments.length === 0 ? <p className="comment-empty">No feedback yet. Start the conversation.</p> : comments.map((comment) => (
            <article className="comment-card" key={comment.id}>
              <div className="comment-meta"><strong>{comment.author_name}</strong><span>{new Date(comment.updated_at).toLocaleDateString()}</span></div>
              <p>{comment.content}</p>
              {canModerate(comment) && <div className="comment-actions">
                <button type="button" onClick={() => { setEditingCommentId(comment.id); setCommentText(comment.content); }}>Edit</button>
                <button type="button" onClick={() => deleteComment(comment.id)}>Delete</button>
              </div>}
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
