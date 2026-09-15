"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

export default function AdminAuditLogsPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getAuditLogs(100)
      .then(setLogs)
      .catch(() => setLogs([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="admin-page admin-detail-page">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "28px" }}>
        <div>
          <div style={{ fontSize: "0.8rem", color: "var(--brand-primary)", fontWeight: 700 }}>
            <Link href="/admin">← Back to Admin Console</Link>
          </div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.02em", marginTop: "4px" }}>
            Immutable Security Audit Logs
          </h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginTop: "4px" }}>
            Append-only records of security events, administrative mutations, and syndication jobs.
          </p>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: "center", padding: "40px" }}>Loading audit records...</div>
      ) : logs.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "40px" }}>
          No audit entries recorded yet.
        </div>
      ) : (
        <div className="card" style={{ padding: "0", overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ background: "var(--bg-secondary)", borderBottom: "1px solid var(--border-subtle)", textAlign: "left" }}>
                <th style={{ padding: "14px 18px", fontWeight: 600 }}>Timestamp</th>
                <th style={{ padding: "14px 18px", fontWeight: 600 }}>Action</th>
                <th style={{ padding: "14px 18px", fontWeight: 600 }}>Resource</th>
                <th style={{ padding: "14px 18px", fontWeight: 600 }}>IP Address</th>
                <th style={{ padding: "14px 18px", fontWeight: 600 }}>Details (Sanitized)</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                  <td style={{ padding: "12px 18px", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
                    {new Date(log.created_at).toLocaleString()}
                  </td>
                  <td style={{ padding: "12px 18px" }}>
                    <span className="badge badge-info" style={{ fontSize: "0.75rem" }}>
                      {log.action}
                    </span>
                  </td>
                  <td style={{ padding: "12px 18px", fontWeight: 600 }}>{log.resource_type}</td>
                  <td style={{ padding: "12px 18px", color: "var(--text-muted)", fontFamily: "var(--font-mono)", fontSize: "0.8rem" }}>
                    {log.ip_address || "127.0.0.1"}
                  </td>
                  <td style={{ padding: "12px 18px", fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                    {JSON.stringify(log.details)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
