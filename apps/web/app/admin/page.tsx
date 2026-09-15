"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { AnalyticsSummary } from "@/lib/types";

const modules = [
  ["Users", "User & role management", "Assign RBAC roles and control active platform access.", "/admin/users", "◉", "Manage users"],
  ["Prompts", "Prompt versioning", "Review and publish auditable versions for all agents.", "/admin/prompts", "✦", "Manage prompts"],
  ["Security", "Security audit logs", "Inspect immutable records of important platform actions.", "/admin/audit", "◇", "View audit trail"],
  ["AI gateway", "AI gateway config", "Configure the active provider and operational controls.", "/settings/providers", "✺", "Configure engine"],
];

export default function AdminDashboardPage() {
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  useEffect(() => { api.getAnalytics().then(setAnalytics).catch(() => setAnalytics(null)); }, []);

  return (
    <section className="admin-page admin-overview">
      <header className="admin-page-header">
        <Link href="/dashboard" className="admin-back-link">← Back to dashboard</Link>
        <span className="eyebrow">Platform controls</span>
        <h1>Admin &amp; governance</h1>
        <p>Manage access, prompt governance, security records, and the secure LLM gateway from one protected console.</p>
      </header>

      <div className="admin-module-grid">
        {modules.map(([kicker, title, description, href, icon, action]) => <Link href={href} className="admin-module-card" key={href}><span className="admin-module-icon">{icon}</span><span className="admin-module-kicker">{kicker}</span><h2>{title}</h2><p>{description}</p><strong>{action} <i>→</i></strong></Link>)}
      </div>

      {analytics && <section className="admin-summary card"><header><div><span className="eyebrow">Live platform signals</span><h2>Operations summary</h2></div><span className="admin-summary-status"><i /> Monitoring active</span></header><div className="admin-stat-grid">
        <div><span>Total registered users</span><strong>{analytics.total_users}</strong></div><div><span>Active users</span><strong className="success-number">{analytics.active_users}</strong></div><div><span>Total articles</span><strong>{analytics.total_articles}</strong></div><div><span>Total tracked cost</span><strong className="cost-number">${analytics.total_cost_usd.toFixed(4)}</strong></div>
      </div></section>}
    </section>
  );
}
