"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { AnalyticsSummary, User } from "@/lib/types";

export default function AdminDashboardPage() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);

  useEffect(() => {
    api.getMe().then(setCurrentUser).catch(() => setCurrentUser(null));
    api.getAnalytics().then(setAnalytics).catch(() => setAnalytics(null));
  }, []);

  const isSuperadmin = currentUser?.is_superadmin === true;

  const modules = [
    isSuperadmin
      ? ["Tenants", "Companies & dedicated DBs", "Manage company databases, subscription plans, and toggle freeze/unfreeze controls.", "/admin/companies", "🏛", "Manage companies"]
      : ["Subscription", "Plan & billing management", "Manage your studio subscription tier, article quotas, and 30-day renewals.", "/admin/subscription", "⚡", "Manage subscription"],
    ["Users", "User & role management", "Assign RBAC roles and control active platform access.", "/admin/users", "◉", "Manage users"],
    ["Prompts", "Prompt versioning", "Review and publish auditable versions for all agents.", "/admin/prompts", "✦", "Manage prompts"],
    ["Security", "Security audit logs", "Inspect immutable records of important platform actions.", "/admin/audit", "◇", "View audit trail"],
    ["AI gateway", "AI gateway config", "Configure the active provider and operational controls.", "/settings/providers", "✺", "Configure engine"],
  ];

  return (
    <section className="admin-page admin-overview">
      <header className="admin-page-header">
        <Link href="/dashboard" className="admin-back-link">← Back to dashboard</Link>
        <span className="eyebrow">{isSuperadmin ? "Platform Superadmin Controls" : "Studio Admin Controls"}</span>
        <h1>{isSuperadmin ? "Admin & governance" : `${currentUser?.company_name || "Studio"} Administration`}</h1>
        <p>
          {isSuperadmin
            ? "Manage access, company databases, prompt governance, and the secure LLM gateway from one protected console."
            : "Manage your team members, studio subscription, prompt settings, and AI engine controls."}
        </p>
      </header>

      <div className="admin-module-grid">
        {modules.map(([kicker, title, description, href, icon, action]) => (
          <Link href={href} className="admin-module-card" key={href}>
            <span className="admin-module-icon">{icon}</span>
            <span className="admin-module-kicker">{kicker}</span>
            <h2>{title}</h2>
            <p>{description}</p>
            <strong>{action} <i>→</i></strong>
          </Link>
        ))}
      </div>

      {analytics && (
        <section className="admin-summary card">
          <header>
            <div>
              <span className="eyebrow">Live platform signals</span>
              <h2>Operations summary</h2>
            </div>
            <span className="admin-summary-status"><i /> Monitoring active</span>
          </header>
          <div className="admin-stat-grid">
            <div><span>Total registered users</span><strong>{analytics.total_users}</strong></div>
            <div><span>Active users</span><strong className="success-number">{analytics.active_users}</strong></div>
            <div><span>Total articles</span><strong>{analytics.total_articles}</strong></div>
            <div><span>Total tracked cost</span><strong className="cost-number">${analytics.total_cost_usd.toFixed(4)}</strong></div>
          </div>
        </section>
      )}
    </section>
  );
}
