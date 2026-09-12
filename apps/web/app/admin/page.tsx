"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { AnalyticsSummary } from "@/lib/types";

export default function AdminDashboardPage() {
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getAnalytics()
      .then(setAnalytics)
      .catch(() => setAnalytics(null))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div style={{ marginBottom: "28px" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.02em" }}>Admin & Governance Console</h1>
        <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginTop: "4px" }}>
          Superadmin and platform management: users, RBAC roles, versioned prompts, and immutable security audit logs.
        </p>
      </div>

      {/* Admin Modules Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "20px", marginBottom: "32px" }}>
        <Link href="/admin/users" className="card" style={{ textDecoration: "none" }}>
          <div style={{ fontSize: "2rem", marginBottom: "10px" }}>👥</div>
          <h3 style={{ fontSize: "1.15rem", fontWeight: 700 }}>User Management</h3>
          <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: "4px" }}>
            Assign RBAC roles (Admin, Editor, Author, Viewer) and toggle active status.
          </p>
          <div style={{ fontSize: "0.8rem", color: "var(--brand-primary)", fontWeight: 600, marginTop: "16px" }}>
            Manage Users →
          </div>
        </Link>

        <Link href="/admin/prompts" className="card" style={{ textDecoration: "none" }}>
          <div style={{ fontSize: "2rem", marginBottom: "10px" }}>📜</div>
          <h3 style={{ fontSize: "1.15rem", fontWeight: 700 }}>Prompt Versioning</h3>
          <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: "4px" }}>
            Audit, edit, and publish versioned system prompts for all 11 autonomous agents.
          </p>
          <div style={{ fontSize: "0.8rem", color: "var(--brand-primary)", fontWeight: 600, marginTop: "16px" }}>
            Manage Prompts →
          </div>
        </Link>

        <Link href="/admin/audit" className="card" style={{ textDecoration: "none" }}>
          <div style={{ fontSize: "2rem", marginBottom: "10px" }}>🛡️</div>
          <h3 style={{ fontSize: "1.15rem", fontWeight: 700 }}>Security Audit Logs</h3>
          <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: "4px" }}>
            Immutable records of logins, publishing, provider reconfiguration, and security events.
          </p>
          <div style={{ fontSize: "0.8rem", color: "var(--brand-primary)", fontWeight: 600, marginTop: "16px" }}>
            View Audit Trail →
          </div>
        </Link>

        <Link href="/settings/providers" className="card" style={{ textDecoration: "none" }}>
          <div style={{ fontSize: "2rem", marginBottom: "10px" }}>⚡</div>
          <h3 style={{ fontSize: "1.15rem", fontWeight: 700 }}>AI Gateway Config</h3>
          <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: "4px" }}>
            Switch active provider, inspect server connection states, and enforce budget ceilings.
          </p>
          <div style={{ fontSize: "0.8rem", color: "var(--brand-primary)", fontWeight: 600, marginTop: "16px" }}>
            Configure Engine →
          </div>
        </Link>
      </div>

      {/* Analytics Summary */}
      {analytics && (
        <div className="card">
          <h3 style={{ fontSize: "1.15rem", fontWeight: 700, marginBottom: "16px" }}>Platform Operations Summary</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px" }}>
            <div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>TOTAL REGISTERED USERS</div>
              <div style={{ fontSize: "1.4rem", fontWeight: 700, marginTop: "4px" }}>{analytics.total_users}</div>
            </div>
            <div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>ACTIVE USERS</div>
              <div style={{ fontSize: "1.4rem", fontWeight: 700, marginTop: "4px", color: "var(--accent-success)" }}>
                {analytics.active_users}
              </div>
            </div>
            <div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>TOTAL ARTICLES</div>
              <div style={{ fontSize: "1.4rem", fontWeight: 700, marginTop: "4px" }}>{analytics.total_articles}</div>
            </div>
            <div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>TOTAL ACCUMULATED COST</div>
              <div style={{ fontSize: "1.4rem", fontWeight: 700, marginTop: "4px", color: "var(--brand-primary)" }}>
                ${analytics.total_cost_usd.toFixed(4)}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
