"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { User } from "@/lib/types";

type PublicArticle = {
  id: string;
  organization_name: string;
  organization_slug: string;
  title: string;
  slug: string;
  summary: string | null;
  target_keywords: string[];
  estimated_reading_time: number;
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export default function PublicBlogHome() {
  const [articles, setArticles] = useState<PublicArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [user, setUser] = useState<User | null>(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.getMe().then(setUser).catch(() => setUser(null));
  }, []);

  useEffect(() => {
    const onDocClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
    };
    if (profileOpen) document.addEventListener("click", onDocClick);
    return () => document.removeEventListener("click", onDocClick);
  }, [profileOpen]);

  const handleLogout = async () => {
    try {
      await api.logout();
    } catch {
      // Local cleanup fallback
    }
    localStorage.removeItem("token");
    setUser(null);
    setProfileOpen(false);
  };

  useEffect(() => {
    fetch(`${API_BASE}/public/articles`)
      .then(async (response) => {
        if (!response.ok) throw new Error("Unable to load published articles.");
        return response.json();
      })
      .then(setArticles)
      .catch((err) => setError(err.message || "Unable to load published articles."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main style={{ maxWidth: "1120px", margin: "0 auto", padding: "32px 24px 80px" }}>
      {/* Top Bar: BlogPilot brand and User Name / Avatar / Actions in the same line */}
      <nav style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: "24px", borderBottom: "1px solid var(--border-subtle)", marginBottom: "46px", flexWrap: "wrap", gap: "16px" }}>
        <Link href="/" style={{ color: "var(--brand-primary)", fontWeight: 800, letterSpacing: "0.08em", fontSize: "0.95rem", textTransform: "uppercase", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "6px" }}>
          <span>✦</span> BlogPilot
        </Link>

        {user ? (
          <div style={{ display: "flex", alignItems: "center", gap: "14px", flexWrap: "wrap" }}>
            <div ref={menuRef} className="profile-menu-wrap" style={{ position: "relative" }}>
              <button
                className="header-profile"
                onClick={() => setProfileOpen((prev) => !prev)}
                aria-expanded={profileOpen}
                style={{ display: "flex", alignItems: "center", gap: "8px", background: "none", border: "none", cursor: "pointer", padding: "4px" }}
              >
                <span className="profile-avatar">{user.full_name ? user.full_name.charAt(0).toUpperCase() : "U"}</span>
                <span style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--text-primary)" }}>{user.full_name}</span>
                <span className="profile-chevron" style={{ fontSize: "12px", color: "var(--text-muted)" }}>⌄</span>
              </button>
              {profileOpen && (
                <div className="profile-popover" style={{ position: "absolute", top: "calc(100% + 8px)", right: 0, zIndex: 100 }}>
                  <div className="profile-popover-identity">
                    <strong>{user.full_name}</strong>
                    <small>{user.email || user.role}</small>
                  </div>
                  <button className="profile-logout" onClick={handleLogout}>
                    <span aria-hidden="true">↪</span> Log out
                  </button>
                </div>
              )}
            </div>
            <Link href="/admin-signup" className="btn btn-secondary">Studio sign up</Link>
          </div>
        ) : (
          <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
            <Link href="/login" className="btn btn-secondary">Studio sign in</Link>
            <Link href="/admin-signup" className="btn btn-primary">Studio sign up</Link>
          </div>
        )}
      </nav>

      {/* Hero Section */}
      <header style={{ marginBottom: "50px" }}>
        <h1 style={{ margin: "0", fontSize: "clamp(2rem, 5vw, 3.75rem)", letterSpacing: "-0.045em" }}>Ideas worth reading.</h1>
        <p style={{ color: "var(--text-secondary)", maxWidth: "600px", fontSize: "1.05rem", lineHeight: 1.7, marginTop: "10px" }}>
          Evidence-led stories and practical insights from every BlogPilot publisher.
        </p>
      </header>

      {loading && <p style={{ color: "var(--text-muted)" }}>Loading published blogs…</p>}
      {error && <div className="card" style={{ color: "var(--accent-danger)", padding: "20px" }}>{error}</div>}
      {!loading && !error && articles.length === 0 && <div className="card" style={{ textAlign: "center", padding: "52px 24px" }}><h2>No published blogs yet</h2><p style={{ color: "var(--text-muted)" }}>Approved articles will appear here once they are published.</p></div>}
      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "20px" }}>
        {articles.map((article) => (
          <article key={article.id} className="card" style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "14px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", color: "var(--text-muted)", fontSize: "0.78rem" }}><span>{article.organization_name}</span><span>{article.estimated_reading_time || 1} min read</span></div>
            <h2 style={{ margin: 0, fontSize: "1.3rem", lineHeight: 1.3 }}>{article.title}</h2>
            <p style={{ color: "var(--text-secondary)", lineHeight: 1.65, margin: 0, flex: 1 }}>{article.summary || "Read the full article and explore the ideas."}</p>
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>{article.target_keywords.slice(0, 3).map((keyword) => <span key={keyword} className="badge badge-info">{keyword}</span>)}</div>
            <Link className="btn btn-primary" href={`/blog/${article.organization_slug}/${article.id}/${article.slug}`}>Read article →</Link>
          </article>
        ))}
      </section>
    </main>
  );
}
