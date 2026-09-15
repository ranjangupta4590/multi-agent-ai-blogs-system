"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { User } from "@/lib/types";

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState<string | null>(null);

  const loadUsers = async () => {
    try {
      const data = await api.getUsers();
      setUsers(data);
    } catch (err: any) {
      setFeedback("Failed to load users: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handleRoleChange = async (userId: string, newRole: string) => {
    try {
      await api.updateUserRole(userId, newRole);
      setFeedback(`Role updated to ${newRole} successfully.`);
      await loadUsers();
    } catch (err: any) {
      setFeedback("Failed to update role: " + err.message);
    }
  };

  const handleToggleActive = async (userId: string, currentStatus: boolean) => {
    try {
      await api.toggleUserActive(userId, !currentStatus);
      setFeedback(`User status set to ${!currentStatus ? "Active" : "Inactive"}.`);
      await loadUsers();
    } catch (err: any) {
      setFeedback("Failed to toggle status: " + err.message);
    }
  };

  return (
    <div className="admin-page admin-detail-page">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "28px" }}>
        <div>
          <div style={{ fontSize: "0.8rem", color: "var(--brand-primary)", fontWeight: 700 }}>
            <Link href="/admin">← Back to Admin Console</Link>
          </div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.02em", marginTop: "4px" }}>
            User & Role Management
          </h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginTop: "4px" }}>
            Manage platform members, assign RBAC permissions, and control access.
          </p>
        </div>
      </div>

      {feedback && (
        <div className="badge-info" style={{ padding: "10px 16px", borderRadius: "var(--radius-md)", marginBottom: "20px" }}>
          {feedback}
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: "center", padding: "40px" }}>Loading users...</div>
      ) : (
        <div className="card" style={{ padding: "0", overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
            <thead>
              <tr style={{ background: "var(--bg-secondary)", borderBottom: "1px solid var(--border-subtle)", textAlign: "left" }}>
                <th style={{ padding: "14px 20px" }}>Name & Email</th>
                <th style={{ padding: "14px 20px" }}>Status</th>
                <th style={{ padding: "14px 20px" }}>Role</th>
                <th style={{ padding: "14px 20px", textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                  <td style={{ padding: "14px 20px" }}>
                    <div style={{ fontWeight: 600 }}>{u.full_name}</div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{u.email}</div>
                  </td>
                  <td style={{ padding: "14px 20px" }}>
                    <span className={`badge ${u.is_active ? "badge-success" : "badge-danger"}`}>
                      {u.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td style={{ padding: "14px 20px" }}>
                    <select
                      className="select"
                      style={{ padding: "4px 8px", fontSize: "0.8rem", width: "140px" }}
                      value={u.role}
                      onChange={(e) => handleRoleChange(u.id, e.target.value)}
                    >
                      <option value="SUPER_ADMIN">SUPER_ADMIN</option>
                      <option value="ADMIN">ADMIN</option>
                      <option value="EDITOR">EDITOR</option>
                      <option value="AUTHOR">AUTHOR</option>
                      <option value="VIEWER">VIEWER</option>
                    </select>
                  </td>
                  <td style={{ padding: "14px 20px", textAlign: "right" }}>
                    <button
                      onClick={() => handleToggleActive(u.id, u.is_active)}
                      className="btn btn-secondary"
                      style={{ padding: "4px 10px", fontSize: "0.75rem" }}
                    >
                      {u.is_active ? "Deactivate" : "Activate"}
                    </button>
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
