"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

interface SubscriptionBarrierProps {
  errorMessage: string;
  onRenewed?: () => void;
}

export default function SubscriptionBarrier({ errorMessage, onRenewed }: SubscriptionBarrierProps) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [renewFeedback, setRenewFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const isBlocked = errorMessage.toLowerCase().includes("blocked") || errorMessage.toLowerCase().includes("freeze");

  const handleSelfRenew = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setRenewFeedback(null);
    try {
      await api.renewCompanyByCredentials({
        email: email.trim(),
        password,
        extend_days: 30,
      });
      setRenewFeedback({
        type: "success",
        text: "Subscription successfully renewed for 30 days! Reloading workspace…",
      });
      setTimeout(() => {
        if (onRenewed) {
          onRenewed();
        } else {
          window.location.reload();
        }
      }, 1200);
    } catch (err: any) {
      setRenewFeedback({
        type: "error",
        text: err.message || "Failed to renew subscription. Check your credentials.",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    router.replace("/login");
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "32px 20px",
        backgroundColor: "var(--bg-primary)",
      }}
    >
      <div
        className="card"
        style={{
          width: "100%",
          maxWidth: "480px",
          padding: "36px",
          borderRadius: "var(--radius-xl)",
          textAlign: "center",
          border: isBlocked ? "1px solid var(--accent-danger)" : "1px solid var(--accent-warning)",
          boxShadow: "var(--shadow-lg)",
          backgroundColor: "var(--bg-surface)",
        }}
      >
        <div
          style={{
            width: "60px",
            height: "60px",
            borderRadius: "50%",
            background: isBlocked ? "var(--accent-danger-bg)" : "var(--accent-warning-bg)",
            color: isBlocked ? "var(--accent-danger)" : "var(--accent-warning)",
            fontSize: "2rem",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: "18px",
          }}
        >
          {isBlocked ? "🔒" : "⏳"}
        </div>

        <h1
          style={{
            fontSize: "1.45rem",
            fontWeight: 800,
            color: "var(--text-primary)",
            marginBottom: "8px",
          }}
        >
          {isBlocked ? "Studio Workspace Frozen" : "Studio Subscription Expired"}
        </h1>

        <div
          style={{
            background: isBlocked ? "var(--accent-danger-bg)" : "var(--accent-warning-bg)",
            padding: "14px 18px",
            borderRadius: "var(--radius-md)",
            fontSize: "0.875rem",
            color: isBlocked ? "var(--accent-danger)" : "#b45309",
            marginBottom: "24px",
            lineHeight: 1.5,
            border: isBlocked ? "1px solid rgba(239, 68, 68, 0.2)" : "1px solid rgba(245, 158, 11, 0.2)",
          }}
        >
          {errorMessage}
        </div>

        {renewFeedback && (
          <div
            className={`badge-${renewFeedback.type === "success" ? "success" : "danger"}`}
            style={{
              padding: "10px 14px",
              borderRadius: "var(--radius-md)",
              fontSize: "0.85rem",
              marginBottom: "16px",
            }}
          >
            {renewFeedback.text}
          </div>
        )}

        {isBlocked ? (
          <div>
            <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", marginBottom: "20px" }}>
              Your dedicated company database has been temporarily blocked by the Superadmin. Please reach out to your platform administrator to unfreeze access.
            </p>
            <button
              onClick={handleLogout}
              className="btn btn-secondary"
              style={{ width: "100%", padding: "10px" }}
            >
              Sign out of account
            </button>
          </div>
        ) : (
          <div>
            <h2
              style={{
                fontSize: "0.95rem",
                fontWeight: 700,
                color: "var(--text-primary)",
                textAlign: "left",
                marginBottom: "12px",
              }}
            >
              ⚡ Instant 30-Day Renewal
            </h2>
            <form onSubmit={handleSelfRenew} style={{ display: "flex", flexDirection: "column", gap: "12px", textAlign: "left" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, marginBottom: "4px", color: "var(--text-secondary)" }}>
                  Admin Email
                </label>
                <input
                  type="email"
                  required
                  className="input"
                  placeholder="admin@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  style={{ width: "100%" }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600, marginBottom: "4px", color: "var(--text-muted)" }}>
                  Password
                </label>
                <input
                  type="password"
                  required
                  className="input"
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  style={{ width: "100%" }}
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="btn btn-primary"
                style={{
                  width: "100%",
                  padding: "12px",
                  fontSize: "0.9rem",
                  fontWeight: 700,
                  marginTop: "6px",
                  borderRadius: "10px",
                }}
              >
                {loading ? "Renewing Subscription…" : "Renew Subscription (30 Days) →"}
              </button>
            </form>

            <div style={{ marginTop: "16px", borderTop: "1px solid var(--border-color)", paddingTop: "14px" }}>
              <button
                onClick={handleLogout}
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  color: "var(--text-muted)",
                  fontSize: "0.85rem",
                }}
              >
                Sign out of account
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
