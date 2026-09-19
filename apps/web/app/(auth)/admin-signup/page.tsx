"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { SubscriptionPlan } from "@/lib/types";

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

export default function StudioSignupPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [selectedPlanId, setSelectedPlanId] = useState("pro_studio");
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadRazorpayScript();

    // If user is already logged in (e.g. as public reader), prefill their name and email
    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    if (token) {
      api.getMe().then((me) => {
        if (me) {
          if (me.full_name) setFullName(me.full_name);
          if (me.email) setEmail(me.email);
        }
      }).catch(() => {});
    }

    const fetchPlans = async () => {
      try {
        const fetched = await api.getSubscriptionPlans();
        if (fetched && fetched.length > 0) {
          setPlans(fetched);
          if (fetched.some((p: SubscriptionPlan) => p.id === "pro_studio")) {
            setSelectedPlanId("pro_studio");
          } else {
            setSelectedPlanId(fetched[0].id);
          }
        }
      } catch (err) {
        setPlans([
          {
            id: "starter_studio",
            name: "Starter Studio",
            description: "Bring your own API key. Ideal for independent publishers.",
            price_monthly_usd: 29.0,
            ai_provider_included: false,
            max_articles_monthly: 10,
            has_fact_checking: false,
            has_wordpress_syndication: false,
            has_advanced_seo: false,
            is_active: true,
          },
          {
            id: "pro_studio",
            name: "Pro Studio",
            description: "Full 11-agent AI Gateway included with automated CMS syndication.",
            price_monthly_usd: 79.0,
            ai_provider_included: true,
            max_articles_monthly: 50,
            has_fact_checking: true,
            has_wordpress_syndication: true,
            has_advanced_seo: true,
            is_active: true,
          },
        ]);
      }
    };
    fetchPlans();
  }, []);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!companyName.trim()) {
      setError("Please enter your Company / Studio Name to set up your workspace.");
      return;
    }
    if (!email.trim() || !fullName.trim() || !password) {
      setError("Please complete all required fields.");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      // 1. Create Razorpay signup order with selected tier
      const order = await api.createRazorpaySignupOrder({
        company_name: companyName.trim(),
        email: email.trim(),
        plan_id: selectedPlanId,
      });

      // 2. Check if Test / Simulation Mode (if credentials not entered yet in .env)
      if (order.is_test_mode) {
        const result = await api.studioSignup({
          company_name: companyName.trim(),
          full_name: fullName.trim(),
          email: email.trim(),
          password,
          plan_id: selectedPlanId,
          razorpay_order_id: order.order_id,
          razorpay_payment_id: `pay_sim_${Date.now()}`,
          razorpay_signature: "simulated_test_signature",
        });
        if (result.access_token) {
          localStorage.setItem("token", result.access_token);
        }
        router.replace("/dashboard");
        return;
      }

      // 3. Real Razorpay Mode - Load script and open checkout modal
      const scriptLoaded = await loadRazorpayScript();
      if (!scriptLoaded) {
        throw new Error("Unable to load Razorpay payment window. Please check your internet connection.");
      }

      const options = {
        key: order.key_id,
        amount: order.amount_paise,
        currency: order.currency,
        name: "BlogPilot Studio",
        description: `${order.plan_name} - 30 Days Studio Workspace`,
        order_id: order.order_id,
        prefill: {
          name: fullName.trim(),
          email: email.trim(),
        },
        theme: {
          color: "#6366f1",
        },
        handler: async function (response: any) {
          try {
            const result = await api.studioSignup({
              company_name: companyName.trim(),
              full_name: fullName.trim(),
              email: email.trim(),
              password,
              plan_id: selectedPlanId,
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            });
            if (result.access_token) {
              localStorage.setItem("token", result.access_token);
            }
            router.replace("/dashboard");
          } catch (err: any) {
            setError(err.message || "Failed to finalize studio registration after payment.");
            setSubmitting(false);
          }
        },
        modal: {
          ondismiss: function () {
            setSubmitting(false);
            setError("Payment checkout window was closed. Complete payment to activate your studio.");
          },
        },
      };

      const rzp = new (window as any).Razorpay(options);
      rzp.open();
    } catch (err: any) {
      setError(err.message || "Failed to initiate studio registration and payment.");
      setSubmitting(false);
    }
  };

  const starterPlan = plans.find((p) => p.id === "starter_studio") || plans[0];
  const proPlan = plans.find((p) => p.id === "pro_studio") || plans[1] || plans[0];

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px 20px",
        backgroundColor: "var(--bg-primary)",
      }}
    >
      <div style={{ width: "100%", maxWidth: "1020px" }}>
        {/* Header Branding */}
        <div style={{ textAlign: "center", marginBottom: "36px" }}>
          <Link
            href="/"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              color: "var(--brand-primary)",
              textDecoration: "none",
              fontSize: "0.9rem",
              fontWeight: 700,
              marginBottom: "12px",
            }}
          >
            ← Back to BlogPilot
          </Link>
          <h1
            style={{
              fontSize: "clamp(1.8rem, 3.5vw, 2.5rem)",
              fontWeight: 800,
              letterSpacing: "-0.03em",
              color: "var(--text-primary)",
              margin: "0 0 8px 0",
            }}
          >
            Create Your Dedicated Studio
          </h1>
          {/* <p
            style={{
              color: "var(--text-secondary)",
              fontSize: "1.05rem",
              maxWidth: "600px",
              margin: "0 auto",
            }}
          >
            Provision an isolated company with autonomous 11-agent AI workflows.
          </p> */}
        </div>

        {error && (
          <div
            className="card"
            style={{
              background: "var(--accent-danger-bg)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              color: "var(--accent-danger)",
              padding: "16px 20px",
              borderRadius: "var(--radius-lg)",
              marginBottom: "24px",
              fontSize: "0.95rem",
            }}
          >
            <strong>Registration Notice:</strong> {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
              gap: "24px",
              marginBottom: "32px",
            }}
          >
            {/* Form Details Card */}
            <div className="card" style={{ padding: "32px", display: "flex", flexDirection: "column", gap: "18px" }}>
              <div style={{ borderBottom: "1px solid var(--border-subtle)", paddingBottom: "14px" }}>
                <h2 style={{ fontSize: "1.3rem", fontWeight: 700, color: "var(--text-primary)", margin: "4px 0 0 0" }}>
                  Studio &amp; Company Profile
                </h2>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: "6px" }}>
                  Company Name *
                </label>
                <input
                  className="input"
                  required
                  placeholder="e.g. Acme Tech Insights"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: "6px" }}>
                  Administrator Full Name *
                </label>
                <input
                  className="input"
                  required
                  placeholder="Jane Doe"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: "6px" }}>
                  Admin Work Email *
                </label>
                <input
                  className="input"
                  type="email"
                  required
                  placeholder="jane@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: "6px" }}>
                  Create Password (min. 8 characters) *
                </label>
                <input
                  className="input"
                  type="password"
                  minLength={8}
                  required
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </div>

            {/* Plan 1 vs Plan 2 Cards */}
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <div style={{ padding: "0 4px 6px" }}>
                <h2 style={{ fontSize: "1.3rem", fontWeight: 700, color: "var(--text-primary)", margin: "4px 0 0 0" }}>
                  Choose Subscription Plan
                </h2>
              </div>

              {/* Starter Studio Card */}
              {starterPlan && (
                <div
                  className="card"
                  onClick={() => setSelectedPlanId(starterPlan.id)}
                  style={{
                    cursor: "pointer",
                    padding: "24px",
                    border: selectedPlanId === starterPlan.id
                      ? "2px solid var(--brand-primary)"
                      : "1px solid var(--border-subtle)",
                    backgroundColor: selectedPlanId === starterPlan.id
                      ? "rgba(14, 165, 233, 0.04)"
                      : "var(--bg-surface)",
                    boxShadow: selectedPlanId === starterPlan.id ? "0 4px 16px var(--brand-glow)" : "var(--shadow-card)",
                    transition: "all 0.2s ease",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "10px" }}>
                    <div>
                      <h3 style={{ margin: 0, fontSize: "1.2rem", fontWeight: 700, color: "var(--text-primary)" }}>
                        {starterPlan.name}
                      </h3>
                      <p style={{ margin: "4px 0 0 0", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                        {starterPlan.description || "Bring your own API key. Ideal for independent publishers."}
                      </p>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <span style={{ fontSize: "1.6rem", fontWeight: 800, color: "var(--text-primary)" }}>
                        ${starterPlan.price_monthly_usd}
                      </span>
                      <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>/mo</span>
                    </div>
                  </div>

                  {/* Feature Checklist */}
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", fontSize: "0.82rem", marginTop: "14px", paddingTop: "14px", borderTop: "1px solid var(--border-subtle)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", color: starterPlan.ai_provider_included ? "var(--accent-success)" : "var(--text-muted)" }}>
                      <span>{starterPlan.ai_provider_included ? "✓" : "✕"}</span>
                      <span>{starterPlan.ai_provider_included ? "Built-in AI Gateway" : "BYOK (Own API Keys)"}</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--accent-success)" }}>
                      <span>✓</span>
                      <span>{starterPlan.max_articles_monthly} articles / month</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", color: starterPlan.has_fact_checking ? "var(--accent-success)" : "var(--text-muted)" }}>
                      <span>{starterPlan.has_fact_checking ? "✓" : "✕"}</span>
                      <span>Autonomous Fact-Check</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", color: starterPlan.has_wordpress_syndication ? "var(--accent-success)" : "var(--text-muted)" }}>
                      <span>{starterPlan.has_wordpress_syndication ? "✓" : "✕"}</span>
                      <span>1-Click CMS Syndication</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--accent-success)" }}>
                      <span>✓</span>
                      <span>Isolated Studio Workspace</span>
                    </div>
                  </div>

                  <div style={{ marginTop: "14px", display: "flex", alignItems: "center", gap: "8px" }}>
                    <input
                      type="radio"
                      name="plan"
                      checked={selectedPlanId === starterPlan.id}
                      onChange={() => setSelectedPlanId(starterPlan.id)}
                    />
                    <span style={{ fontSize: "0.85rem", fontWeight: 700, color: selectedPlanId === starterPlan.id ? "var(--brand-primary)" : "var(--text-secondary)" }}>
                      {selectedPlanId === starterPlan.id ? "Selected Plan" : "Choose Starter"}
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
                    position: "relative",
                    border: selectedPlanId === proPlan.id
                      ? "2px solid #8b5cf6"
                      : "1px solid var(--border-subtle)",
                    backgroundColor: selectedPlanId === proPlan.id
                      ? "rgba(139, 92, 246, 0.04)"
                      : "var(--bg-surface)",
                    boxShadow: selectedPlanId === proPlan.id ? "0 4px 20px rgba(139, 92, 246, 0.18)" : "var(--shadow-card)",
                    transition: "all 0.2s ease",
                  }}
                >
                  <div
                    style={{
                      position: "absolute",
                      top: "-10px",
                      right: "20px",
                      background: "var(--brand-gradient)",
                      color: "#fff",
                      fontSize: "0.7rem",
                      fontWeight: 800,
                      padding: "2px 10px",
                      borderRadius: "var(--radius-full)",
                      letterSpacing: "0.04em",
                      textTransform: "uppercase",
                      boxShadow: "0 2px 8px var(--brand-glow)",
                    }}
                  >
                    Recommended
                  </div>

                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "10px" }}>
                    <div>
                      <h3 style={{ margin: 0, fontSize: "1.2rem", fontWeight: 700, color: "var(--text-primary)" }}>
                        {proPlan.name}
                      </h3>
                      <p style={{ margin: "4px 0 0 0", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                        {proPlan.description || "Full 11-agent AI Gateway included with automated CMS syndication."}
                      </p>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <span style={{ fontSize: "1.6rem", fontWeight: 800, color: "var(--text-primary)" }}>
                        ${proPlan.price_monthly_usd}
                      </span>
                      <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>/mo</span>
                    </div>
                  </div>

                  {/* Feature Checklist */}
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", fontSize: "0.82rem", marginTop: "14px", paddingTop: "14px", borderTop: "1px solid var(--border-subtle)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--accent-success)" }}>
                      <span>✓</span>
                      <strong style={{ color: "var(--accent-purple)" }}>Built-in AI Gateway</strong>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--accent-success)" }}>
                      <span>✓</span>
                      <span>{proPlan.max_articles_monthly} articles / month</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--accent-success)" }}>
                      <span>✓</span>
                      <span>Autonomous Fact-Check</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--accent-success)" }}>
                      <span>✓</span>
                      <span>1-Click CMS Syndication</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--accent-success)" }}>
                      <span>✓</span>
                      <span>Advanced JSON-LD SEO</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--accent-success)" }}>
                      <span>✓</span>
                      <span>Isolated Studio Workspace</span>
                    </div>
                  </div>

                  <div style={{ marginTop: "14px", display: "flex", alignItems: "center", gap: "8px" }}>
                    <input
                      type="radio"
                      name="plan"
                      checked={selectedPlanId === proPlan.id}
                      onChange={() => setSelectedPlanId(proPlan.id)}
                    />
                    <span style={{ fontSize: "0.85rem", fontWeight: 700, color: selectedPlanId === proPlan.id ? "var(--accent-purple)" : "var(--text-secondary)" }}>
                      {selectedPlanId === proPlan.id ? "Selected Plan" : "Choose Pro"}
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Submit Action Button */}
          <div style={{ textAlign: "center" }}>
            <button
              type="submit"
              disabled={submitting}
              className="btn btn-primary"
              style={{
                minWidth: "280px",
                padding: "14px 32px",
                fontSize: "1rem",
                fontWeight: 700,
                borderRadius: "var(--radius-md)",
              }}
            >
              {submitting ? "Opening Razorpay & Activating Studio…" : "Create Studio & Launch Dashboard →"}
            </button>
            <div style={{ marginTop: "16px" }}>
              <span style={{ fontSize: "0.875rem", color: "var(--text-secondary)" }}>
                Already registered your studio?{" "}
                <Link href="/login" style={{ color: "var(--brand-primary)", fontWeight: 700 }}>
                  Sign in here
                </Link>
              </span>
            </div>
          </div>
        </form>
      </div>
    </main>
  );
}
