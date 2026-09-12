"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import ActiveProviderBadge from "@/components/layout/ActiveProviderBadge";
import ThemeToggle from "@/components/layout/ThemeToggle";
import { api } from "@/lib/api";
import { User } from "@/lib/types";

export default function Header() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    api.getMe()
      .then(setUser)
      .catch(() => setUser(null));
  }, []);

  return (
    <header className="app-header">
      {/* Search Bar */}
      <div style={{ display: "flex", alignItems: "center", gap: "10px", width: "320px" }}>
        <input
          type="text"
          placeholder="Search articles, projects, claims..."
          className="input"
          style={{ padding: "6px 12px", fontSize: "0.85rem", height: "36px" }}
        />
      </div>

      {/* Right controls */}
      <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
        {/* Active AI Engine Badge */}
        <ActiveProviderBadge />

        {/* Theme Toggle */}
        <ThemeToggle />

        {/* User profile / session */}
        {user ? (
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div
              style={{
                width: "34px",
                height: "34px",
                borderRadius: "50%",
                background: "var(--brand-gradient)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#fff",
                fontWeight: 600,
                fontSize: "0.85rem",
              }}
            >
              {user.full_name.charAt(0).toUpperCase()}
            </div>
            <div style={{ display: "flex", flexDirection: "column" }}>
              <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>{user.full_name}</span>
              <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>{user.role}</span>
            </div>
          </div>
        ) : (
          <Link href="/login" className="btn btn-primary" style={{ padding: "6px 14px", fontSize: "0.8rem" }}>
            Sign In
          </Link>
        )}
      </div>
    </header>
  );
}
