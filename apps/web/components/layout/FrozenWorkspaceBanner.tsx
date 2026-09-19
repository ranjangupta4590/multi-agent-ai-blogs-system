"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { SubscriptionPlan, User } from "@/lib/types";

interface FrozenWorkspaceBannerProps {
  user: User | null;
  onPlanRenewed?: () => void;
}

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

export default function FrozenWorkspaceBanner({ user, onPlanRenewed }: FrozenWorkspaceBannerProps) {
  const [showModal, setShowModal] = useState(false);
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState("pro_studio");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [payingWithRazorpay, setPayingWithRazorpay] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    if (user?.email) {
      setEmail(user.email);
    }
  }, [user]);

  useEffect(() => {
    if (showModal) {
      loadRazorpayScript();
      api.getSubscriptionPlans().then((fetched) => {
        if (fetched && fetched.length > 0) {
          setPlans(fetched);
          if (fetched.some((p: SubscriptionPlan) => p.id === "pro_studio")) {
            setSelectedPlanId("pro_studio");
          } else {
            setSelectedPlanId(fetched[0].id);
          }
        }
      }).catch(() => {});
    }
  }, [showModal]);

  if (!user?.is_frozen) {
    return null;
  }

  const handleRazorpayCheckout = async () => {
    setPayingWithRazorpay(true);
    setFeedback(null);
    try {
      const order = await api.createRazorpayOrder({ plan_id: selectedPlanId, extend_days: 30 });

      if (order.is_test_mode) {
        await api.verifyRazorpayPayment({
          razorpay_order_id: order.order_id,
          razorpay_payment_id: `pay_sim_${Date.now()}`,
          razorpay_signature: "simulated_test_signature",
        });
        setFeedback({
          type: "success",
          text: "[Razorpay Simulation Mode] Payment verified! Workspace unlocked for 30 days.",
        });
        setTimeout(() => {
          setShowModal(false);
          if (onPlanRenewed) onPlanRenewed();
          else window.location.reload();
        }, 1200);
        return;
      }

      const scriptLoaded = await loadRazorpayScript();
      if (!scriptLoaded) throw new Error("Could not load payment script. Check internet.");

      const options = {
        key: order.key_id,
        amount: order.amount_paise,
        currency: order.currency,
        name: "BlogPilot Studio",
        description: `${order.plan_name} - 30 Days`,
        order_id: order.order_id,
        prefill: { email: order.admin_email, name: order.company_name },
        theme: { color: "#6366f1" },
        handler: async function (response: any) {
          try {
            await api.verifyRazorpayPayment({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            });
            setFeedback({ type: "success", text: "Payment verified! Workspace unlocked." });
            setTimeout(() => {
              setShowModal(false);
              if (onPlanRenewed) onPlanRenewed();
              else window.location.reload();
            }, 1200);
          } catch (err: any) {
            setFeedback({ type: "error", text: err.message || "Payment verification failed." });
          }
        },
        modal: { ondismiss: () => setPayingWithRazorpay(false) },
      };

      const rzp = new (window as any).Razorpay(options);
      rzp.open();
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message || "Razorpay initiation failed." });
    } finally {
      setPayingWithRazorpay(false);
    }
  };

  const handleRenew = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password) {
      setFeedback({ type: "error", text: "Please enter your password to confirm renewal." });
      return;
    }
    setLoading(true);
    setFeedback(null);
    try {
      await api.renewCompanyByCredentials({
        email: email || user.email,
        password,
        extend_days: 30,
      });
      setFeedback({
        type: "success",
        text: "Subscription successfully renewed for 30 days! Restoring full access…",
      });
      setTimeout(() => {
        setShowModal(false);
        if (onPlanRenewed) {
          onPlanRenewed();
        } else {
          window.location.reload();
        }
      }, 1200);
    } catch (err: any) {
      setFeedback({
        type: "error",
        text: err.message || "Failed to renew subscription. Check your credentials.",
      });
    } finally {
      setLoading(false);
    }
  };

  const starterPlan = plans.find((p) => p.id === "starter_studio") || plans[0];
  const proPlan = plans.find((p) => p.id === "pro_studio") || plans[1] || plans[0];

  return (
    <>
      {/* Top Banner */}
      <div
        style={{
          background: "linear-gradient(90deg, #fef3c7 0%, #fee2e2 100%)",
          borderBottom: "1px solid #fcd34d",
          padding: "10px 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "12px",
          zIndex: 50,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "1.2rem" }}>🔒</span>
          <div>
            <strong style={{ color: "#991b1b", fontSize: "0.9rem" }}>
              Studio Workspace Frozen / Subscription Expired:
            </strong>{" "}
            <span style={{ color: "#78350f", fontSize: "0.85rem" }}>
              {user.blocked_reason || "All AI generation, articles, and publishing are locked. Purchase or renew a plan to restore access."}
            </span>
          </div>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="btn btn-primary"
          style={{
            padding: "6px 16px",
            fontSize: "0.85rem",
            fontWeight: 700,
            borderRadius: "var(--radius-full)",
            boxShadow: "0 2px 8px rgba(239, 68, 68, 0.25)",
          }}
        >
          ⚡ Purchase / Renew Plan
        </button>
      </div>

      {/* Plan Purchase / Renew Modal */}
      {showModal && (
        <div
          className="modal-overlay"
          onClick={() => !loading && setShowModal(false)}
        >
          <div
            className="modal-content card"
            onClick={(e) => e.stopPropagation()}
            style={{
              maxWidth: "680px",
              padding: "32px",
              maxHeight: "90vh",
              overflowY: "auto",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px" }}>
              <div>
                <span className="eyebrow" style={{ color: "var(--brand-primary)", fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase" }}>
                  Instant Restoration
                </span>
                <h2 style={{ fontSize: "1.4rem", fontWeight: 800, color: "var(--text-primary)", margin: "4px 0 0 0" }}>
                  Purchase or Renew Studio Plan
                </h2>
                <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", margin: "4px 0 0 0" }}>
                  Select your tier and extend your dedicated company database subscription by 30 days.
                </p>
              </div>
              <button
                onClick={() => setShowModal(false)}
                style={{ background: "none", border: "none", fontSize: "1.2rem", cursor: "pointer", color: "var(--text-muted)" }}
              >
                ✕
              </button>
            </div>

            {feedback && (
              <div
                className={`card ${feedback.type === "success" ? "badge-success" : "badge-danger"}`}
                style={{ padding: "10px 14px", marginBottom: "16px", borderRadius: "8px", fontSize: "0.85rem" }}
              >
                {feedback.text}
              </div>
            )}

            {/* 2 Plan Cards */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "20px" }}>
              {starterPlan && (
                <div
                  className="card"
                  onClick={() => setSelectedPlanId(starterPlan.id)}
                  style={{
                    cursor: "pointer",
                    padding: "16px",
                    border: selectedPlanId === starterPlan.id ? "2px solid var(--brand-primary)" : "1px solid var(--border-subtle)",
                    backgroundColor: selectedPlanId === starterPlan.id ? "rgba(14, 165, 233, 0.04)" : "var(--bg-surface)",
                    borderRadius: "var(--radius-lg)",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                    <h4 style={{ margin: 0, fontSize: "1.05rem", fontWeight: 700 }}>{starterPlan.name}</h4>
                    <span style={{ fontSize: "1.2rem", fontWeight: 800 }}>${starterPlan.price_monthly_usd}<small style={{ fontSize: "0.75rem", fontWeight: 400 }}>/mo</small></span>
                  </div>
                  <ul style={{ listStyle: "none", padding: 0, margin: "12px 0 0 0", fontSize: "0.78rem", display: "flex", flexDirection: "column", gap: "6px", color: "var(--text-secondary)" }}>
                    <li>{starterPlan.ai_provider_included ? "✓ Built-in AI" : "✕ BYOK (Own AI Keys)"}</li>
                    <li>✓ {starterPlan.max_articles_monthly} articles / month</li>
                    <li>{starterPlan.has_fact_checking ? "✓ Fact-checking" : "✕ Manual review only"}</li>
                    <li>✓ Dedicated Studio Workspace</li>
                  </ul>
                  <div style={{ marginTop: "12px" }}>
                    <input type="radio" checked={selectedPlanId === starterPlan.id} onChange={() => setSelectedPlanId(starterPlan.id)} />
                    <span style={{ fontSize: "0.8rem", fontWeight: 600, marginLeft: "6px" }}>Starter Tier</span>
                  </div>
                </div>
              )}

              {proPlan && (
                <div
                  className="card"
                  onClick={() => setSelectedPlanId(proPlan.id)}
                  style={{
                    cursor: "pointer",
                    padding: "16px",
                    position: "relative",
                    border: selectedPlanId === proPlan.id ? "2px solid #8b5cf6" : "1px solid var(--border-subtle)",
                    backgroundColor: selectedPlanId === proPlan.id ? "rgba(139, 92, 246, 0.04)" : "var(--bg-surface)",
                    borderRadius: "var(--radius-lg)",
                  }}
                >
                  <span style={{ position: "absolute", top: "-8px", right: "12px", background: "var(--brand-gradient)", color: "#fff", fontSize: "0.65rem", fontWeight: 800, padding: "2px 8px", borderRadius: "10px" }}>
                    RECOMMENDED
                  </span>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                    <h4 style={{ margin: 0, fontSize: "1.05rem", fontWeight: 700 }}>{proPlan.name}</h4>
                    <span style={{ fontSize: "1.2rem", fontWeight: 800 }}>${proPlan.price_monthly_usd}<small style={{ fontSize: "0.75rem", fontWeight: 400 }}>/mo</small></span>
                  </div>
                  <ul style={{ listStyle: "none", padding: 0, margin: "12px 0 0 0", fontSize: "0.78rem", display: "flex", flexDirection: "column", gap: "6px", color: "var(--text-secondary)" }}>
                    <li style={{ color: "var(--accent-purple)", fontWeight: 700 }}>✓ Built-in AI Gateway Included</li>
                    <li>✓ {proPlan.max_articles_monthly} articles / month</li>
                    <li>✓ Autonomous Fact-check loop</li>
                    <li>✓ 1-Click CMS Syndication</li>
                  </ul>
                  <div style={{ marginTop: "12px" }}>
                    <input type="radio" checked={selectedPlanId === proPlan.id} onChange={() => setSelectedPlanId(proPlan.id)} />
                    <span style={{ fontSize: "0.8rem", fontWeight: 600, marginLeft: "6px", color: "var(--accent-purple)" }}>Pro Tier</span>
                  </div>
                </div>
              )}
            </div>

            {/* Instant Checkout */}
            <div style={{ marginBottom: "18px" }}>
              <button
                type="button"
                onClick={handleRazorpayCheckout}
                disabled={payingWithRazorpay}
                className="btn btn-primary"
                style={{
                  width: "100%",
                  padding: "14px",
                  fontSize: "1rem",
                  fontWeight: 800,
                  borderRadius: "var(--radius-md)",
                  background: "linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)",
                  boxShadow: "0 4px 14px rgba(79, 70, 229, 0.35)",
                }}
              >
                {payingWithRazorpay ? "Opening Gateway…" : "Pay & Activate (30 Days)"}
              </button>
            </div>

            <div style={{ textAlign: "center", margin: "4px 0 16px 0", color: "var(--text-muted)", fontSize: "0.8rem" }}>
              — or verify with admin password —
            </div>

            {/* Renewal Form */}
            <form onSubmit={handleRenew} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: "4px" }}>
                  Confirm Admin Password *
                </label>
                <input
                  className="input"
                  type="password"
                  required
                  placeholder="Enter your account password to verify renewal"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="btn btn-primary"
                style={{
                  width: "100%",
                  padding: "12px",
                  fontSize: "0.95rem",
                  fontWeight: 700,
                  marginTop: "6px",
                  borderRadius: "var(--radius-md)",
                }}
              >
                {loading ? "Renewing Subscription…" : "⚡ Confirm & Extend Subscription (30 Days)"}
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
