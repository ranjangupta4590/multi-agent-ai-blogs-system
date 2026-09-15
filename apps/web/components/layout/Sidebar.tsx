"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { label: "Dashboard", href: "/dashboard", icon: "▦", group: "Content studio" },
  { label: "Projects", href: "/projects", icon: "▱" },
  { label: "Articles", href: "/articles", icon: "✦" },
  { label: "Sources & Grounding", href: "/sources", icon: "⌕" },
  { label: "SEO Intelligence", href: "/seo", icon: "↗" },
  { label: "Public Publishing", href: "/publishing", icon: "◉" },
  { label: "AI Providers", href: "/settings/providers", icon: "✺", group: "System & operations" },
  { label: "Admin Console", href: "/admin", icon: "◇" },
];

type SidebarProps = {
  collapsed: boolean;
  mobileOpen: boolean;
  onToggle: () => void;
  onCloseMobile: () => void;
};

export default function Sidebar({ collapsed, mobileOpen, onToggle, onCloseMobile }: SidebarProps) {
  const pathname = usePathname();

  return (
    <aside className={`app-sidebar ${collapsed ? "is-collapsed" : ""} ${mobileOpen ? "is-mobile-open" : ""}`} aria-label="Main navigation">
      <div className="sidebar-top">
        <Link href="/dashboard" className="brand-mark" aria-label="BlogPilot dashboard" onClick={onCloseMobile}>
          <span className="brand-icon">✦</span>
          <span className="brand-copy">
            <strong>BlogPilot</strong>
            <small>Multi-Agent Blog Studio</small>
          </span>
        </Link>
        <button className="sidebar-collapse-toggle" onClick={onToggle} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} title={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
          <span>{collapsed ? "›" : "‹"}</span>
        </button>
        <button className="sidebar-mobile-close" onClick={onCloseMobile} aria-label="Close navigation">×</button>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item, index) => {
          const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
          return (
            <React.Fragment key={item.href}>
              {item.group && <p className={`sidebar-group ${index ? "with-space" : ""}`}>{item.group}</p>}
              <Link
                href={item.href}
                className={`sidebar-link ${isActive ? "is-active" : ""}`}
                title={collapsed ? item.label : undefined}
                onClick={onCloseMobile}
              >
                <span className="sidebar-icon" aria-hidden="true">{item.icon}</span>
                <span className="sidebar-label">{item.label}</span>
                {item.label === "Sources & Grounding" && <span className="sidebar-status">Safe</span>}
              </Link>
            </React.Fragment>
          );
        })}
      </nav>

    </aside>
  );
}
