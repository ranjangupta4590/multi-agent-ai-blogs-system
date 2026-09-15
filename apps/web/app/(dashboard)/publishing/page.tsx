"use client";

import Link from "next/link";

export default function PublishingOverviewPage() {
  return (
    <div style={{ maxWidth: "880px" }}>
      <div style={{ marginBottom: "28px" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.02em" }}>Public Blog Publishing</h1>
        <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginTop: "4px" }}>Publish approved articles directly to the built-in BlogPilot public home page.</p>
      </div>
      <div className="glass-panel" style={{ padding: "24px", borderLeft: "4px solid var(--accent-success)" }}>
        <div style={{ fontSize: "0.8rem", textTransform: "uppercase", color: "var(--accent-success)", fontWeight: 700 }}>Human review required</div>
        <h2 style={{ fontSize: "1.25rem", fontWeight: 700, marginTop: "6px" }}>Your article stays private until you publish it.</h2>
        <p style={{ color: "var(--text-secondary)", marginTop: "8px", lineHeight: 1.65 }}>Generate the article, review its sources and claims, then select Human Approve. An approved article can be published publicly without any external CMS account or credentials.</p>
        <Link href="/articles" className="btn btn-primary" style={{ display: "inline-block", marginTop: "18px" }}>Open Articles →</Link>
      </div>
    </div>
  );
}
