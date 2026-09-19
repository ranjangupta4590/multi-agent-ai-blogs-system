"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { CompanyTenant, SubscriptionPlan, User } from "@/lib/types";

export default function AdminCompaniesPage() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [companies, setCompanies] = useState<CompanyTenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Editing state for plans
  const [editingPlanId, setEditingPlanId] = useState<string | null>(null);
  const [planPrice, setPlanPrice] = useState<number>(0);
  const [planMaxArticles, setPlanMaxArticles] = useState<number>(10);
  const [savingPlan, setSavingPlan] = useState(false);

  // Freeze modal state
  const [freezingCompany, setFreezingCompany] = useState<CompanyTenant | null>(null);
  const [freezeReason, setFreezeReason] = useState("");
  const [actionInProgress, setActionInProgress] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const user = await api.getMe().catch(() => null);
      setCurrentUser(user);
      if (user && !user.is_superadmin) {
        setLoading(false);
        return;
      }
      const [fetchedPlans, fetchedCompanies] = await Promise.all([
        api.getSubscriptionPlans(),
        api.getCompanies(),
      ]);
      setPlans(fetchedPlans);
      setCompanies(fetchedCompanies);
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message || "Failed to load companies or plans." });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleStartEditPlan = (plan: SubscriptionPlan) => {
    setEditingPlanId(plan.id);
    setPlanPrice(plan.price_monthly_usd);
    setPlanMaxArticles(plan.max_articles_monthly);
  };

  const handleSavePlan = async (planId: string) => {
    setSavingPlan(true);
    setFeedback(null);
    try {
      await api.updateSubscriptionPlan(planId, {
        price_monthly_usd: Number(planPrice),
        max_articles_monthly: Number(planMaxArticles),
      });
      setFeedback({ type: "success", text: "Subscription plan pricing updated successfully." });
      setEditingPlanId(null);
      await loadData();
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message || "Failed to update plan." });
    } finally {
      setSavingPlan(false);
    }
  };

  const handleFreeze = async () => {
    if (!freezingCompany) return;
    setActionInProgress(true);
    setFeedback(null);
    try {
      await api.freezeCompany(freezingCompany.id, freezeReason || "Administrative freeze");
      setFeedback({
        type: "success",
        text: `Company ${freezingCompany.company_name} workspace successfully blocked/frozen.`,
      });
      setFreezingCompany(null);
      setFreezeReason("");
      await loadData();
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message || "Failed to freeze company." });
    } finally {
      setActionInProgress(false);
    }
  };

  const handleUnfreeze = async (company: CompanyTenant) => {
    if (!confirm(`Are you sure you want to unfreeze ${company.company_name} and restore database access?`)) return;
    setActionInProgress(true);
    setFeedback(null);
    try {
      await api.unfreezeCompany(company.id);
      setFeedback({
        type: "success",
        text: `Company ${company.company_name} successfully unblocked and active.`,
      });
      await loadData();
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message || "Failed to unfreeze company." });
    } finally {
      setActionInProgress(false);
    }
  };

  const handleRenew = async (company: CompanyTenant, extendDays: number = 30) => {
    if (!confirm(`Extend subscription for ${company.company_name} by ${extendDays} days?`)) return;
    setActionInProgress(true);
    setFeedback(null);
    try {
      await api.renewCompany(company.id, extendDays);
      setFeedback({
        type: "success",
        text: `Subscription for ${company.company_name} extended by ${extendDays} days.`,
      });
      await loadData();
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message || "Failed to extend subscription." });
    } finally {
      setActionInProgress(false);
    }
  };

  if (currentUser && !currentUser.is_superadmin) {
    return (
      <div className="admin-page" style={{ maxWidth: "680px", margin: "60px auto", textAlign: "center", padding: "32px 24px" }}>
        <div className="card" style={{ padding: "40px 24px" }}>
          <span style={{ fontSize: "2.5rem" }}>🔒</span>
          <h2 style={{ fontSize: "1.4rem", fontWeight: 800, margin: "16px 0 8px" }}>Superadmin Access Only</h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.95rem", maxWidth: "480px", margin: "0 auto 24px" }}>
            The Platform Tenants console is reserved for the platform Superadmin. As a Studio Admin, you can manage your subscription, quotas, and billing directly from your Subscription Management page.
          </p>
          <div style={{ display: "flex", gap: "12px", justifyContent: "center" }}>
            <Link href="/admin/subscription" className="btn btn-primary">
              ⚡ Go to My Subscription
            </Link>
            <Link href="/dashboard" className="btn btn-secondary">
              ← Dashboard
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-page admin-detail-page" style={{ maxWidth: "1200px", margin: "0 auto", padding: "32px 24px" }}>
      <header className="admin-users-header" style={{ marginBottom: "28px" }}>
        <div>
          <Link href="/admin" className="admin-back-link">
            ← Back to Admin Console
          </Link>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 800, margin: "8px 0 4px 0" }}>
            Company Tenants &amp; Workspaces
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.95rem" }}>
            Manage tenant studio workspaces, customize subscription plans, and toggle freeze/unfreeze controls.
          </p>
        </div>
      </header>

      {feedback && (
        <div
          className={`card ${feedback.type === "success" ? "badge-success" : "badge-danger"}`}
          style={{
            padding: "12px 18px",
            marginBottom: "24px",
            borderRadius: "10px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span>{feedback.text}</span>
          <button
            onClick={() => setFeedback(null)}
            style={{ background: "none", border: "none", cursor: "pointer", color: "inherit", fontWeight: 700 }}
          >
            ✕
          </button>
        </div>
      )}

      {/* SECTION 1: EDITABLE SUBSCRIPTION PLANS */}
      <section style={{ marginBottom: "40px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <div>
            <h2 style={{ fontSize: "1.25rem", fontWeight: 700, margin: 0 }}>
              ⚡ Studio Subscription Plans &amp; Pricing
            </h2>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", margin: "4px 0 0 0" }}>
              Superadmin can set customized pricing and quotas for both Studio tiers.
            </p>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "20px" }}>
          {plans.map((plan) => {
            const isEditing = editingPlanId === plan.id;
            return (
              <div
                key={plan.id}
                className="card"
                style={{
                  padding: "24px",
                  borderRadius: "16px",
                  border: plan.id === "pro_studio" ? "2px solid #8b5cf6" : "1px solid var(--border-subtle)",
                  position: "relative",
                  background: "var(--bg-surface)",
                }}
              >
                {plan.id === "pro_studio" && (
                  <span
                    style={{
                      position: "absolute",
                      top: "-10px",
                      right: "20px",
                      background: "linear-gradient(135deg, #6366f1, #a855f7)",
                      color: "#fff",
                      fontSize: "0.7rem",
                      fontWeight: 700,
                      padding: "2px 10px",
                      borderRadius: "12px",
                      textTransform: "uppercase",
                    }}
                  >
                    Pro Tier
                  </span>
                )}

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "12px" }}>
                  <h3 style={{ margin: 0, fontSize: "1.2rem", fontWeight: 700 }}>{plan.name}</h3>
                  <div>
                    {isEditing ? (
                      <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                        <span style={{ fontSize: "1.2rem", fontWeight: 700 }}>$</span>
                        <input
                          type="number"
                          className="input"
                          value={planPrice}
                          onChange={(e) => setPlanPrice(Number(e.target.value))}
                          style={{ width: "80px", padding: "4px 8px" }}
                          min="0"
                        />
                        <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>/mo</span>
                      </div>
                    ) : (
                      <span style={{ fontSize: "1.4rem", fontWeight: 800, color: "var(--text-primary)" }}>
                        ${plan.price_monthly_usd}
                        <small style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 400 }}>/mo</small>
                      </span>
                    )}
                  </div>
                </div>

                <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem", marginBottom: "16px" }}>
                  {plan.description}
                </p>

                {/* Features & Quota */}
                <div style={{ fontSize: "0.85rem", display: "flex", flexDirection: "column", gap: "8px", marginBottom: "20px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span>{plan.ai_provider_included ? "✓" : "❌"}</span>
                    <span>{plan.ai_provider_included ? "Built-in AI Gateway Included" : "BYOK (Own API Keys)"}</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span>✓</span>
                    {isEditing ? (
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <input
                          type="number"
                          className="input"
                          value={planMaxArticles}
                          onChange={(e) => setPlanMaxArticles(Number(e.target.value))}
                          style={{ width: "70px", padding: "2px 6px" }}
                          min="1"
                        />
                        <span>articles / month</span>
                      </div>
                    ) : (
                      <span>Max {plan.max_articles_monthly} articles / month</span>
                    )}
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span>{plan.has_fact_checking ? "✓" : "❌"}</span>
                    <span>Real-time Fact Checking Loop</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span>{plan.has_wordpress_syndication ? "✓" : "❌"}</span>
                    <span>1-Click WordPress &amp; CMS Syndication</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span>{plan.has_advanced_seo ? "✓" : "❌"}</span>
                    <span>Technical JSON-LD SEO &amp; Clustering</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span>✓</span>
                    <span>Studio Workspace Provisioning</span>
                  </div>
                </div>

                {/* Plan Edit Actions */}
                <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "14px", display: "flex", justifyContent: "flex-end", gap: "8px" }}>
                  {isEditing ? (
                    <>
                      <button
                        className="btn btn-secondary"
                        onClick={() => setEditingPlanId(null)}
                        disabled={savingPlan}
                        style={{ padding: "6px 12px", fontSize: "0.85rem" }}
                      >
                        Cancel
                      </button>
                      <button
                        className="btn btn-primary"
                        onClick={() => handleSavePlan(plan.id)}
                        disabled={savingPlan}
                        style={{ padding: "6px 14px", fontSize: "0.85rem" }}
                      >
                        {savingPlan ? "Saving…" : "Save Changes"}
                      </button>
                    </>
                  ) : (
                    <button
                      className="btn btn-secondary"
                      onClick={() => handleStartEditPlan(plan)}
                      style={{ padding: "6px 12px", fontSize: "0.85rem" }}
                    >
                      ✎ Edit Price &amp; Quota
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* SECTION 2: COMPANY DATABASES & ACCESS CONTROL */}
      <section>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <div>
            <h2 style={{ fontSize: "1.25rem", fontWeight: 700, margin: 0 }}>
              🏛 Dedicated Company Databases &amp; Workspaces
            </h2>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", margin: "4px 0 0 0" }}>
              Live directory of company tenants with dedicated database names and 1-click freeze/unfreeze controls.
            </p>
          </div>
          <button
            onClick={loadData}
            className="btn btn-secondary"
            style={{ padding: "6px 12px", fontSize: "0.85rem" }}
          >
            ↻ Refresh List
          </button>
        </div>

        {loading ? (
          <div className="card" style={{ textAlign: "center", padding: "40px", color: "var(--text-muted)" }}>
            Loading company databases…
          </div>
        ) : companies.length === 0 ? (
          <div className="card" style={{ textAlign: "center", padding: "48px 24px" }}>
            <h3>No Company Databases Provisioned Yet</h3>
            <p style={{ color: "var(--text-muted)", marginTop: "8px" }}>
              Companies that sign up via Studio Signup will have their dedicated databases automatically registered here.
            </p>
          </div>
        ) : (
          <div className="card" style={{ overflowX: "auto", padding: 0, borderRadius: "16px" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.875rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-subtle)", background: "var(--bg-secondary)" }}>
                  <th style={{ padding: "14px 18px" }}>Company &amp; Database</th>
                  <th style={{ padding: "14px 18px" }}>Admin Contact</th>
                  <th style={{ padding: "14px 18px" }}>Plan</th>
                  <th style={{ padding: "14px 18px" }}>Status</th>
                  <th style={{ padding: "14px 18px" }}>Subscription Expires</th>
                  <th style={{ padding: "14px 18px", textAlign: "right" }}>Governance Actions</th>
                </tr>
              </thead>
              <tbody>
                {companies.map((company) => {
                  const isBlocked = company.is_blocked;
                  const isExpired = company.subscription_status === "EXPIRED";
                  const expDate = new Date(company.subscription_expires_at).toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                  });

                  return (
                    <tr
                      key={company.id}
                      style={{
                        borderBottom: "1px solid var(--border-subtle)",
                        background: isBlocked ? "rgba(239, 68, 68, 0.04)" : "transparent",
                      }}
                    >
                      <td style={{ padding: "14px 18px" }}>
                        <div style={{ fontWeight: 700, color: "var(--text-primary)" }}>{company.company_name}</div>
                        <div style={{ fontFamily: "monospace", fontSize: "0.75rem", color: "#818cf8", marginTop: "2px" }}>
                          🗄 {company.db_name}
                        </div>
                      </td>
                      <td style={{ padding: "14px 18px", color: "var(--text-secondary)" }}>
                        {company.admin_email}
                      </td>
                      <td style={{ padding: "14px 18px" }}>
                        <span
                          className="badge"
                          style={{
                            background: company.plan_id === "pro_studio" ? "rgba(139, 92, 246, 0.15)" : "rgba(255,255,255,0.08)",
                            color: company.plan_id === "pro_studio" ? "#c084fc" : "var(--text-secondary)",
                            fontSize: "0.75rem",
                            padding: "3px 8px",
                            borderRadius: "6px",
                          }}
                        >
                          {company.plan_id === "pro_studio" ? "Pro Studio" : "Starter Studio"}
                        </span>
                      </td>
                      <td style={{ padding: "14px 18px" }}>
                        {isBlocked ? (
                          <span className="badge badge-danger" title={company.blocked_reason || "Frozen by admin"}>
                            Blocked / Frozen
                          </span>
                        ) : isExpired ? (
                          <span className="badge badge-warning">
                            Expired
                          </span>
                        ) : (
                          <span className="badge badge-success">
                            Active
                          </span>
                        )}
                        {company.blocked_reason && (
                          <div style={{ fontSize: "0.7rem", color: "var(--accent-danger)", marginTop: "2px" }}>
                            {company.blocked_reason}
                          </div>
                        )}
                      </td>
                      <td style={{ padding: "14px 18px", color: isExpired ? "var(--accent-danger)" : "var(--text-secondary)" }}>
                        {expDate}
                      </td>
                      <td style={{ padding: "14px 18px", textAlign: "right" }}>
                        <div style={{ display: "inline-flex", gap: "8px", alignItems: "center" }}>
                          {isBlocked ? (
                            <button
                              onClick={() => handleUnfreeze(company)}
                              disabled={actionInProgress}
                              className="btn btn-primary"
                              style={{ padding: "4px 10px", fontSize: "0.78rem" }}
                            >
                              🔓 Unfreeze
                            </button>
                          ) : (
                            <button
                              onClick={() => {
                                setFreezingCompany(company);
                                setFreezeReason("");
                              }}
                              disabled={actionInProgress}
                              className="btn btn-secondary"
                              style={{ padding: "4px 10px", fontSize: "0.78rem", color: "var(--accent-danger)" }}
                            >
                              🔒 Freeze
                            </button>
                          )}

                          <button
                            onClick={() => handleRenew(company, 30)}
                            disabled={actionInProgress}
                            className="btn btn-secondary"
                            style={{ padding: "4px 10px", fontSize: "0.78rem" }}
                            title="Extend expiration date by 30 days"
                          >
                            +30 Days
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Freeze Reason Modal */}
      {freezingCompany && (
        <div
          className="modal-overlay"
          onClick={() => !actionInProgress && setFreezingCompany(null)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.7)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "20px",
          }}
        >
          <div
            className="modal-content card"
            onClick={(e) => e.stopPropagation()}
            style={{ width: "100%", maxWidth: "460px", padding: "28px" }}
          >
            <h3 style={{ margin: "0 0 8px 0", fontSize: "1.25rem", color: "var(--accent-danger)" }}>
              🔒 Freeze Company Workspace
            </h3>
            <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", margin: "0 0 16px 0" }}>
              Freezing <strong>{freezingCompany.company_name}</strong> will instantly block all access to their dedicated database{" "}
              <code>{freezingCompany.db_name}</code>.
            </p>

            <div style={{ marginBottom: "20px" }}>
              <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, marginBottom: "6px" }}>
                Reason for Freezing (Optional):
              </label>
              <input
                className="input"
                placeholder="e.g. Subscription payment dispute / Compliance review"
                value={freezeReason}
                onChange={(e) => setFreezeReason(e.target.value)}
                style={{ width: "100%" }}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setFreezingCompany(null)}
                disabled={actionInProgress}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleFreeze}
                disabled={actionInProgress}
                style={{ background: "var(--accent-danger)", borderColor: "var(--accent-danger)" }}
              >
                {actionInProgress ? "Freezing…" : "Confirm Freeze"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
