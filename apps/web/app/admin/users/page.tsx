"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { User } from "@/lib/types";

const roleLabel: Record<string, string> = { ADMIN: "Admin — internal, full access", PORTAL_USER: "Portal user — limited workspace access", PUBLIC_USER: "Public user — public site only" };

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [showInvite, setShowInvite] = useState(false);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("PORTAL_USER");
  const [inviting, setInviting] = useState(false);
  const loadUsers = async () => { try { setUsers(await api.getUsers()); } catch (err: any) { setFeedback("Failed to load users: " + err.message); } finally { setLoading(false); } };
  useEffect(() => { loadUsers(); }, []);
  const changeRole = async (id: string, next: string) => { try { await api.updateUserRole(id, next); setFeedback("Role updated successfully."); await loadUsers(); } catch (err: any) { setFeedback(err.message || "Unable to update role."); } };
  const toggle = async (id: string, active: boolean) => { try { await api.toggleUserActive(id, !active); setFeedback(`User ${!active ? "activated" : "deactivated"}.`); await loadUsers(); } catch (err: any) { setFeedback(err.message || "Unable to update user."); } };
  const invite = async (event: React.FormEvent) => { event.preventDefault(); setInviting(true); setFeedback(null); try { await api.createUser({ full_name: fullName, email, role }); setFeedback("Account created and temporary-password invitation email sent."); setFullName(""); setEmail(""); setRole("PORTAL_USER"); setShowInvite(false); await loadUsers(); } catch (err: any) { setFeedback(err.message || "User could not be created. Confirm SMTP is configured server-side."); } finally { setInviting(false); } };
  return <div className="admin-page admin-detail-page"><header className="admin-users-header"><div><Link href="/admin" className="admin-back-link">← Back to Admin Console</Link><h1>User &amp; role management</h1><p>Admins create internal accounts. Public users only register themselves and cannot access the workspace.</p></div><button className="btn btn-primary" onClick={() => setShowInvite(true)}>+ Create internal user</button></header>{feedback && <div className="badge-info admin-feedback">{feedback}</div>}{showInvite && <div className="modal-overlay" onClick={() => !inviting && setShowInvite(false)}><section className="modal-content invite-modal" onClick={(event) => event.stopPropagation()}><header><h2>Create internal user</h2><p>A temporary password will be generated server-side and sent only to this email.</p></header><form onSubmit={invite}><label>Full name<input className="input" required value={fullName} onChange={(event) => setFullName(event.target.value)} /></label><label>Email address<input className="input" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label><label>Role<select className="select" value={role} onChange={(event) => setRole(event.target.value)}><option value="PORTAL_USER">Portal user — limited workspace access</option><option value="ADMIN">Admin — internal, full access</option></select></label><div className="invite-actions"><button type="button" className="btn btn-secondary" onClick={() => setShowInvite(false)}>Cancel</button><button className="btn btn-primary" disabled={inviting}>{inviting ? "Sending invitation…" : "Create & email invitation"}</button></div></form></section></div>}{loading ? <div className="loading-state">Loading users…</div> : <div className="card admin-users-table"><table><thead><tr><th>Name &amp; email</th><th>Status</th><th>Role</th><th>Actions</th></tr></thead><tbody>{users.map((user) => <tr key={user.id}><td><strong>{user.full_name}</strong><small>{user.email}</small></td><td><span className={`badge ${user.is_active ? "badge-success" : "badge-danger"}`}>{user.is_active ? "Active" : "Inactive"}</span></td><td><select className="select" value={user.role} onChange={(event) => changeRole(user.id, event.target.value)}>{Object.entries(roleLabel).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></td><td><button onClick={() => toggle(user.id, user.is_active)} className="btn btn-secondary">{user.is_active ? "Deactivate" : "Activate"}</button></td></tr>)}</tbody></table></div>}</div>;
}
