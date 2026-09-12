"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { label: "Dashboard", href: "/dashboard", icon: "📊" },
  { label: "Projects", href: "/projects", icon: "📁" },
  { label: "Articles", href: "/articles", icon: "✍️" },
  { label: "Sources & Grounding", href: "/sources", icon: "🔍" },
  { label: "SEO Intelligence", href: "/seo", icon: "🎯" },
  { label: "Publishing", href: "/publishing", icon: "🚀" },
  { label: "AI Providers", href: "/settings/providers", icon: "⚡" },
  { label: "Admin Console", href: "/admin", icon: "🛡️" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="app-sidebar">
      {/* Brand Header */}
      <div style={{ padding: "24px 20px", borderBottom: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", gap: "10px" }}>
        <div style={{
          width: "34px",
          height: "34px",
          borderRadius: "8px",
          background: "var(--brand-gradient)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#fff",
          fontWeight: 800,
          fontSize: "1.1rem"
        }}>
          A
        </div>
        <div>
          <div style={{ fontWeight: 700, fontSize: "0.95rem", letterSpacing: "-0.02em" }}>Antigravity</div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Multi-Agent Blog Platform</div>
        </div>
      </div>

      {/* Navigation */}
      <nav style={{ padding: "16px 12px", flex: 1, display: "flex", flexDirection: "column", gap: "4px" }}>
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname?.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                padding: "10px 14px",
                borderRadius: "var(--radius-md)",
                fontSize: "0.875rem",
                fontWeight: isActive ? 600 : 500,
                color: isActive ? "var(--brand-primary)" : "var(--text-secondary)",
                backgroundColor: isActive ? "var(--brand-glow)" : "transparent",
                border: isActive ? "1px solid rgba(59, 130, 246, 0.2)" : "1px solid transparent",
                transition: "all 0.15s ease",
              }}
            >
              <span style={{ fontSize: "1.1rem" }}>{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer Info */}
      <div style={{ padding: "16px", borderTop: "1px solid var(--border-subtle)", fontSize: "0.75rem", color: "var(--text-muted)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
          <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "var(--accent-success)" }} />
          <span>v1.0.0 Production Core</span>
        </div>
        <div>Single-Provider Operational</div>
      </div>
    </aside>
  );
}
