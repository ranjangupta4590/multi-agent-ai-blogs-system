"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { CompanyTenant, PaymentTransaction, SubscriptionPlan, User } from "@/lib/types";

function loadRazorpayScript(): Promise<boolean> {
  return new Promise((resolve) => {
    if (typeof window === "undefined") return resolve(false);
    if ((window as any).Razorpay) return resolve(true);
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

export default function TenantSubscriptionPage() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [tenant, setTenant] = useState<CompanyTenant | null>(null);
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [transactions, setTransactions] = useState<PaymentTransaction[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<string>("pro_studio");
  const [extendDays, setExtendDays] = useState<number>(30);
  const [loading, setLoading] = useState(true);
  const [payingWithRazorpay, setPayingWithRazorpay] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [user, myTenant, planList, txList] = await Promise.all([
        api.getMe().catch(() => null),
        api.getMySubscription().catch(() => null),
        api.getSubscriptionPlans().catch(() => []),
        api.getMyPaymentTransactions().catch(() => []),
      ]);
      setCurrentUser(user);
      setTenant(myTenant);
      setPlans(planList);
      setTransactions(txList || []);

      if (myTenant?.plan_id) {
        setSelectedPlanId(myTenant.plan_id);
      } else if (user?.plan_id) {
        setSelectedPlanId(user.plan_id);
      }
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message || "Failed to load subscription details." });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    loadRazorpayScript();
  }, []);

  const handleRazorpayCheckout = async () => {
    setPayingWithRazorpay(true);
    setFeedback(null);
    try {
      const order = await api.createRazorpayOrder({ plan_id: selectedPlanId, extend_days: extendDays });

      if (order.is_test_mode) {
        // Simulation / Test Mode when real keys are not entered yet in .env
        await api.verifyRazorpayPayment({
          razorpay_order_id: order.order_id,
          razorpay_payment_id: `pay_sim_${Date.now()}`,
          razorpay_signature: "simulated_test_signature",
        });
        setFeedback({
          type: "success",
          text: `[Razorpay Simulation / Test Mode] Payment verified! Workspace unlocked & extended for ${extendDays} days.`,
        });
        await loadData();
        return;
      }

      const scriptLoaded = await loadRazorpayScript();
      if (!scriptLoaded) {
        throw new Error("Unable to load Razorpay payment window. Please check your internet connection.");
      }

      const options = {
        key: order.key_id,
        amount: order.amount_paise,
        currency: order.currency,
        name: "BlogPilot Studio",
        description: `${order.plan_name} - ${extendDays} Days Subscription`,
        order_id: order.order_id,
        prefill: {
          email: order.admin_email,
          name: order.company_name,
        },
        theme: {
          color: "#6366f1",
        },
        handler: async function (response: any) {
          try {
            await api.verifyRazorpayPayment({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            });
            setFeedback({
              type: "success",
              text: `Payment verified! Subscription extended for ${extendDays} days. Studio is active.`,
            });
            await loadData();
          } catch (err: any) {
            setFeedback({ type: "error", text: err.message || "Payment verification failed." });
          }
        },
        modal: {
          ondismiss: function () {
            setPayingWithRazorpay(false);
          },
        },
      };

      const rzp = new (window as any).Razorpay(options);
      rzp.open();
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message || "Failed to initiate Razorpay checkout." });
    } finally {
      setPayingWithRazorpay(false);
    }
  };

  const activePlan = plans.find((p) => p.id === (tenant?.plan_id || currentUser?.plan_id || "starter_studio"));
  const starterPlan = plans.find((p) => p.id === "starter_studio") || plans[0];
  const proPlan = plans.find((p) => p.id === "pro_studio") || plans[1] || plans[0];

  const isFrozen = Boolean(
    tenant?.is_blocked ||
    currentUser?.is_frozen ||
    tenant?.subscription_status === "BLOCKED" ||
    currentUser?.subscription_status === "BLOCKED"
  );
  const isExpired = Boolean(
    tenant?.subscription_status === "EXPIRED" || currentUser?.subscription_status === "EXPIRED"
  );

  // Pay & Activate section appears only when workspace requires activation (frozen or expired)
  // or when an active user explicitly selects a different plan tier to upgrade.
  const requiresActivation = isFrozen || isExpired;
  const isSwitchingPlan = Boolean(selectedPlanId && activePlan && selectedPlanId !== activePlan.id);
  const showPaymentSection = requiresActivation || isSwitchingPlan;

  const expiresAt = tenant?.subscription_expires_at
    ? new Date(tenant.subscription_expires_at)
    : currentUser?.subscription_expires_at
    ? new Date(currentUser.subscription_expires_at)
    : null;

  const now = new Date();
  const daysRemaining = expiresAt ? Math.max(0, Math.ceil((expiresAt.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))) : 0;

  return (
    <div className="admin-page admin-detail-page" style={{ maxWidth: "1080px", margin: "0 auto", padding: "32px 24px" }}>
      <header className="admin-users-header" style={{ marginBottom: "28px" }}>
        <div>
          <Link href="/admin" className="admin-back-link">
            ← Back to Admin Console
          </Link>
          <span className="eyebrow" style={{ display: "block", marginTop: "8px" }}>
            Workspace Billing
          </span>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 800, margin: "4px 0 6px 0" }}>
            Studio Subscription &amp; Plan Management
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.95rem" }}>
            Manage your workspace subscription, active article limits, and plan details.
          </p>
        </div>
      </header>

      {feedback && (
        <div
          className={`card ${feedback.type === "success" ? "badge-success" : "badge-danger"}`}
          style={{
            padding: "14px 20px",
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

      {loading ? (
        <div className="card" style={{ padding: "48px 24px", textAlign: "center", color: "var(--text-muted)" }}>
          Loading your company subscription details…
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "28px" }}>
          {/* SECTION 1: CURRENT STATUS HERO CARD */}
          <section className="card" style={{ padding: "28px", borderRadius: "16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px" }}>
              <div>
                <span className="eyebrow" style={{ color: "var(--brand-primary)", fontWeight: 700 }}>
                  Workspace Subscription
                </span>
                <h2 style={{ fontSize: "1.5rem", fontWeight: 800, margin: "4px 0 2px 0" }}>
                  {tenant?.company_name || currentUser?.company_name || "Company Studio"}
                </h2>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", marginTop: "6px" }}>
                  <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                    Admin: {tenant?.admin_email || currentUser?.email}
                  </span>
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                {isFrozen ? (
                  <span className="badge badge-danger" style={{ padding: "6px 14px", fontSize: "0.85rem", fontWeight: 700 }}>
                    🔒 Blocked / Frozen
                  </span>
                ) : isExpired ? (
                  <span className="badge badge-warning" style={{ padding: "6px 14px", fontSize: "0.85rem", fontWeight: 700 }}>
                    ⚠️ Subscription Expired
                  </span>
                ) : (
                  <span className="badge badge-success" style={{ padding: "6px 14px", fontSize: "0.85rem", fontWeight: 700 }}>
                    ✓ Active Subscription
                  </span>
                )}
                <span className="badge" style={{ padding: "6px 12px", background: "var(--brand-gradient)", color: "#fff", fontWeight: 700, fontSize: "0.85rem" }}>
                  {activePlan?.name || "Pro Studio"}
                </span>
              </div>
            </div>

            {/* Quota & Expiry Grid */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                gap: "16px",
                marginTop: "24px",
                paddingTop: "20px",
                borderTop: "1px solid var(--border-subtle)",
              }}
            >
              <div>
                <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", display: "block" }}>Monthly Pricing</span>
                <strong style={{ fontSize: "1.3rem", color: "var(--text-primary)" }}>
                  ${activePlan?.price_monthly_usd ?? 79}<small style={{ fontSize: "0.8rem", fontWeight: 400 }}> / month</small>
                </strong>
              </div>

              <div>
                <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", display: "block" }}>Article Creation Quota</span>
                <strong style={{ fontSize: "1.3rem", color: "var(--text-primary)" }}>
                  {activePlan?.max_articles_monthly ?? 50} <small style={{ fontSize: "0.8rem", fontWeight: 400 }}>articles / mo</small>
                </strong>
              </div>

              <div>
                <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", display: "block" }}>Subscription Validity</span>
                <strong style={{ fontSize: "1.1rem", color: isExpired ? "var(--accent-danger)" : "var(--text-primary)" }}>
                  {expiresAt ? expiresAt.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }) : "Active"}
                </strong>
                <span style={{ display: "block", fontSize: "0.75rem", color: daysRemaining < 5 ? "var(--accent-danger)" : "var(--accent-success)", fontWeight: 600 }}>
                  {isExpired ? "Expired" : `${daysRemaining} days remaining`}
                </span>
              </div>

              <div>
                <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", display: "block" }}>AI Engine Mode</span>
                <strong style={{ fontSize: "1.1rem", color: activePlan?.ai_provider_included ? "var(--accent-purple)" : "var(--text-primary)" }}>
                  {activePlan?.ai_provider_included ? "Built-in AI Gateway" : "BYOK (Own API Keys)"}
                </strong>
              </div>
            </div>

            {isFrozen && (
              <div style={{ marginTop: "18px", padding: "12px 16px", background: "var(--accent-danger-bg)", borderRadius: "8px", border: "1px solid rgba(239,68,68,0.3)", color: "var(--accent-danger)", fontSize: "0.88rem" }}>
                <strong>Freeze Notice:</strong> {tenant?.blocked_reason || currentUser?.blocked_reason || "Your company workspace has been suspended. Please complete renewal to restore full access."}
              </div>
            )}
          </section>

          {/* SECTION 2: CHOOSE / SWITCH PLAN CARDS */}
          <section>
            <h3 style={{ fontSize: "1.2rem", fontWeight: 700, margin: "0 0 14px 0" }}>
              Available Subscription Tiers
            </h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "20px" }}>
              {/* Starter Studio Card */}
              {starterPlan && (
                <div
                  className="card"
                  onClick={() => setSelectedPlanId(starterPlan.id)}
                  style={{
                    cursor: "pointer",
                    padding: "24px",
                    border: selectedPlanId === starterPlan.id ? "2px solid var(--brand-primary)" : "1px solid var(--border-subtle)",
                    backgroundColor: selectedPlanId === starterPlan.id ? "rgba(14, 165, 233, 0.04)" : "var(--bg-surface)",
                    borderRadius: "var(--radius-lg)",
                    position: "relative",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                    <div>
                      <h4 style={{ margin: 0, fontSize: "1.15rem", fontWeight: 700 }}>{starterPlan.name}</h4>
                      <p style={{ margin: "4px 0 0 0", fontSize: "0.82rem", color: "var(--text-secondary)" }}>
                        {starterPlan.description || "Self-managed API keys. Perfect for individual brands."}
                      </p>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <span style={{ fontSize: "1.5rem", fontWeight: 800 }}>${starterPlan.price_monthly_usd}</span>
                      <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>/mo</span>
                    </div>
                  </div>

                  <ul style={{ listStyle: "none", padding: 0, margin: "16px 0", fontSize: "0.82rem", display: "flex", flexDirection: "column", gap: "8px", color: "var(--text-secondary)" }}>
                    <li>{starterPlan.ai_provider_included ? "✓ Built-in AI Gateway" : "✕ BYOK (Bring Your Own API Keys)"}</li>
                    <li>✓ Max {starterPlan.max_articles_monthly} articles / month</li>
                    <li>{starterPlan.has_fact_checking ? "✓ Fact-checking Loop" : "✕ Manual Fact-checking"}</li>
                    <li>{starterPlan.has_wordpress_syndication ? "✓ 1-Click CMS Publishing" : "✕ Manual Publishing"}</li>
                    <li>✓ Dedicated Studio Workspace</li>
                  </ul>

                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "12px" }}>
                    <input
                      type="radio"
                      name="plan_choice"
                      checked={selectedPlanId === starterPlan.id}
                      onChange={() => setSelectedPlanId(starterPlan.id)}
                    />
                    <span style={{ fontSize: "0.85rem", fontWeight: 600, color: selectedPlanId === starterPlan.id ? "var(--brand-primary)" : "var(--text-secondary)" }}>
                      {tenant?.plan_id === starterPlan.id ? "Current Active Tier" : "Select Starter Tier"}
                    </span>
                  </div>
                </div>
              )}

              {/* Pro Studio Card */}
              {proPlan && (
                <div
                  className="card"
                  onClick={() => setSelectedPlanId(proPlan.id)}
                  style={{
                    cursor: "pointer",
                    padding: "24px",
                    border: selectedPlanId === proPlan.id ? "2px solid #8b5cf6" : "1px solid var(--border-subtle)",
                    backgroundColor: selectedPlanId === proPlan.id ? "rgba(139, 92, 246, 0.04)" : "var(--bg-surface)",
                    borderRadius: "var(--radius-lg)",
                    position: "relative",
                  }}
                >
                  <span style={{ position: "absolute", top: "-10px", right: "20px", background: "var(--brand-gradient)", color: "#fff", fontSize: "0.68rem", fontWeight: 800, padding: "2px 10px", borderRadius: "12px", textTransform: "uppercase" }}>
                    Recommended
                  </span>

                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                    <div>
                      <h4 style={{ margin: 0, fontSize: "1.15rem", fontWeight: 700 }}>{proPlan.name}</h4>
                      <p style={{ margin: "4px 0 0 0", fontSize: "0.82rem", color: "var(--text-secondary)" }}>
                        {proPlan.description || "Fully managed 11-agent AI Gateway with automated verification."}
                      </p>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <span style={{ fontSize: "1.5rem", fontWeight: 800 }}>${proPlan.price_monthly_usd}</span>
                      <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>/mo</span>
                    </div>
                  </div>

                  <ul style={{ listStyle: "none", padding: 0, margin: "16px 0", fontSize: "0.82rem", display: "flex", flexDirection: "column", gap: "8px", color: "var(--text-secondary)" }}>
                    <li style={{ color: "var(--accent-purple)", fontWeight: 700 }}>✓ Built-in AI Gateway Included</li>
                    <li>✓ Max {proPlan.max_articles_monthly} articles / month</li>
                    <li>✓ Autonomous Fact-checking Grounding Loop</li>
                    <li>✓ 1-Click WordPress &amp; CMS Syndication</li>
                    <li>✓ Technical JSON-LD SEO Optimization</li>
                    <li>✓ Dedicated Studio Workspace</li>
                  </ul>

                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "12px" }}>
                    <input
                      type="radio"
                      name="plan_choice"
                      checked={selectedPlanId === proPlan.id}
                      onChange={() => setSelectedPlanId(proPlan.id)}
                    />
                    <span style={{ fontSize: "0.85rem", fontWeight: 600, color: selectedPlanId === proPlan.id ? "#8b5cf6" : "var(--text-secondary)" }}>
                      {tenant?.plan_id === proPlan.id ? "Current Active Tier" : "Upgrade to Pro Studio"}
                    </span>
                  </div>
                </div>
              )}
            </div>
          </section>

          {/* SECTION 3: PAY & ACTIVATE (Only shown when account requires activation or user is upgrading) */}
          {showPaymentSection && (
            <section
              className="card"
              style={{
                padding: "24px 28px",
                borderRadius: "16px",
                border: "2px solid #6366f1",
                background: "linear-gradient(180deg, rgba(99, 102, 241, 0.04) 0%, rgba(255,255,255,1) 100%)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
                <div>
                  <h3 style={{ fontSize: "1.3rem", fontWeight: 800, margin: "0 0 4px 0" }}>
                    {isSwitchingPlan && !requiresActivation ? "Upgrade & Activate" : "Pay & Activate"}
                  </h3>
                  <p style={{ color: "var(--text-secondary)", fontSize: "0.88rem", margin: 0 }}>
                    {isFrozen
                      ? "Your workspace is currently suspended. Complete renewal to restore full access."
                      : isSwitchingPlan
                      ? `Switching to ${plans.find((p) => p.id === selectedPlanId)?.name || "selected tier"}. Activate your new subscription.`
                      : "Renew your subscription to maintain uninterrupted studio access."}
                  </p>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <select
                    className="input"
                    value={extendDays}
                    onChange={(e) => setExtendDays(Number(e.target.value))}
                    style={{ width: "150px", padding: "10px" }}
                  >
                    <option value={30}>30 Days (1 Mo)</option>
                    <option value={60}>60 Days (2 Mo)</option>
                    <option value={90}>90 Days (3 Mo)</option>
                  </select>

                  <button
                    type="button"
                    onClick={handleRazorpayCheckout}
                    disabled={payingWithRazorpay}
                    className="btn btn-primary"
                    style={{
                      padding: "11px 26px",
                      fontWeight: 700,
                      fontSize: "0.92rem",
                      borderRadius: "var(--radius-full)",
                      background: "linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)",
                      boxShadow: "0 4px 16px rgba(79, 70, 229, 0.3)",
                    }}
                  >
                    {payingWithRazorpay
                      ? "Opening Gateway…"
                      : isSwitchingPlan && !requiresActivation
                      ? "Upgrade & Activate"
                      : "Pay & Activate"}
                  </button>
                </div>
              </div>
            </section>
          )}

          {/* SECTION 4: BILLING HISTORY & DOWNLOADABLE RECEIPTS */}
          <section className="card" style={{ padding: "28px", borderRadius: "16px" }}>
            <div style={{ marginBottom: "20px" }}>
              <span className="eyebrow" style={{ color: "var(--brand-primary)", fontWeight: 700 }}>
                Billing Records
              </span>
              <h3 style={{ fontSize: "1.3rem", fontWeight: 800, margin: "4px 0 4px 0" }}>
                🧾 Billing History &amp; Receipts
              </h3>
              <p style={{ color: "var(--text-secondary)", fontSize: "0.88rem", margin: 0 }}>
                View all payment transactions, subscription extensions, and download or print official receipts.
              </p>
            </div>

            {transactions.length === 0 ? (
              <div
                style={{
                  padding: "32px",
                  textAlign: "center",
                  background: "var(--bg-primary)",
                  borderRadius: "12px",
                  border: "1px dashed var(--border-subtle)",
                  color: "var(--text-muted)",
                  fontSize: "0.9rem",
                }}
              >
                No payment transactions recorded yet. Any payments completed via Razorpay will appear here with downloadable receipts.
              </div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.88rem" }}>
                  <thead>
                    <tr style={{ borderBottom: "2px solid var(--border-subtle)", textAlign: "left" }}>
                      <th style={{ padding: "10px 12px", color: "var(--text-secondary)", fontWeight: 600 }}>Date</th>
                      <th style={{ padding: "10px 12px", color: "var(--text-secondary)", fontWeight: 600 }}>Plan Tier</th>
                      <th style={{ padding: "10px 12px", color: "var(--text-secondary)", fontWeight: 600 }}>Amount</th>
                      <th style={{ padding: "10px 12px", color: "var(--text-secondary)", fontWeight: 600 }}>Razorpay Payment ID</th>
                      <th style={{ padding: "10px 12px", color: "var(--text-secondary)", fontWeight: 600 }}>Status</th>
                      <th style={{ padding: "10px 12px", color: "var(--text-secondary)", fontWeight: 600, textAlign: "right" }}>Receipt</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transactions.map((tx) => (
                      <tr key={tx.id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                        <td style={{ padding: "14px 12px", color: "var(--text-primary)", whiteSpace: "nowrap" }}>
                          {new Date(tx.created_at).toLocaleDateString("en-US", {
                            year: "numeric",
                            month: "short",
                            day: "numeric",
                          })}
                        </td>
                        <td style={{ padding: "14px 12px" }}>
                          <span style={{ fontWeight: 700, color: "var(--text-primary)" }}>{tx.plan_name}</span>
                          <span style={{ display: "block", fontSize: "0.75rem", color: "var(--text-muted)" }}>
                            +{tx.extend_days} Days
                          </span>
                        </td>
                        <td style={{ padding: "14px 12px", fontWeight: 700, color: "var(--text-primary)" }}>
                          {tx.amount_formatted}
                        </td>
                        <td style={{ padding: "14px 12px" }}>
                          <code
                            style={{
                              background: "rgba(99, 102, 241, 0.08)",
                              color: "var(--brand-primary)",
                              padding: "3px 8px",
                              borderRadius: "4px",
                              fontSize: "0.8rem",
                            }}
                          >
                            {tx.razorpay_payment_id || "Simulated"}
                          </code>
                        </td>
                        <td style={{ padding: "14px 12px" }}>
                          {tx.status === "CAPTURED" ? (
                            <span className="badge badge-success" style={{ padding: "4px 10px", fontSize: "0.78rem" }}>
                              ✓ Paid
                            </span>
                          ) : tx.status === "CREATED" ? (
                            <span className="badge badge-warning" style={{ padding: "4px 10px", fontSize: "0.78rem" }}>
                              Pending
                            </span>
                          ) : (
                            <span className="badge badge-danger" style={{ padding: "4px 10px", fontSize: "0.78rem" }}>
                              {tx.status}
                            </span>
                          )}
                        </td>
                        <td style={{ padding: "14px 12px", textAlign: "right" }}>
                          <button
                            type="button"
                            onClick={() => window.open(api.getReceiptUrl(tx.id), "_blank")}
                            className="btn btn-secondary"
                            style={{
                              padding: "6px 14px",
                              fontSize: "0.8rem",
                              fontWeight: 600,
                              borderRadius: "var(--radius-md)",
                              cursor: "pointer",
                            }}
                          >
                            📥 Download / Print
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
