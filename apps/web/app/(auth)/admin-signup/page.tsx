"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function AdminSignupPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setLoading(true); setError(null);
    try {
      const result = await api.adminSignup({ full_name: fullName, email, password });
      localStorage.setItem("token", result.access_token);
      router.replace("/dashboard");
    } catch (err: any) { setError(err.message || "Admin signup is unavailable."); }
    finally { setLoading(false); }
  };
  return <main className="auth-page"><section className="card auth-card"><span className="eyebrow">Secure bootstrap</span><h1>Admin signup</h1><p>Available only while BlogPilot has no Admin account. Once an Admin exists, they create internal accounts from the Admin Console.</p>{error && <p className="auth-error">{error}</p>}<form onSubmit={submit}><label>Full name<input className="input" required value={fullName} onChange={(event) => setFullName(event.target.value)} /></label><label>Email address<input className="input" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label><label>Create password<input className="input" type="password" minLength={12} required value={password} onChange={(event) => setPassword(event.target.value)} /></label><button className="btn btn-primary" disabled={loading}>{loading ? "Creating Admin…" : "Create first Admin"}</button></form><Link href="/login">← Back to sign in</Link></section></main>;
}
