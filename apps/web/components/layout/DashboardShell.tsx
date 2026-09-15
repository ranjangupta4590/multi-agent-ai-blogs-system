"use client";

import React, { useEffect, useState } from "react";
import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";

export default function DashboardShell({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const saved = window.localStorage.getItem("blogpilot_sidebar_collapsed");
    setCollapsed(saved === "true");
  }, []);

  const toggleCollapsed = () => {
    setCollapsed((current) => {
      const next = !current;
      window.localStorage.setItem("blogpilot_sidebar_collapsed", String(next));
      return next;
    });
  };

  return (
    <div className={`app-container ${collapsed ? "sidebar-is-collapsed" : ""}`}>
      <Sidebar
        collapsed={collapsed}
        mobileOpen={mobileOpen}
        onToggle={toggleCollapsed}
        onCloseMobile={() => setMobileOpen(false)}
      />
      {mobileOpen && <button className="mobile-nav-backdrop" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
      <div className="app-main">
        <Header onOpenMobileMenu={() => setMobileOpen(true)} />
        <main className="page-content">{children}</main>
      </div>
    </div>
  );
}
