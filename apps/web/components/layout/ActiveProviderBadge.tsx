"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { AIProvider } from "@/lib/types";

export default function ActiveProviderBadge() {
  const [activeProvider, setActiveProvider] = useState<AIProvider | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const providers = await api.getProviders();
        const active = providers.find((p) => p.is_active);
        setActiveProvider(active || null);
      } catch (err) {
        // Fallback gracefully
        setActiveProvider(null);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return <div className="badge badge-info">Detecting AI Engine...</div>;
  }

  if (!activeProvider) {
    return (
      <Link href="/settings/providers" className="badge badge-warning" style={{ textDecoration: "none" }}>
        <span style={{ fontSize: "1rem" }}>⚠️</span> No AI Provider Configured
      </Link>
    );
  }

  return (
    <Link href="/settings/providers" className="active-provider-pill" style={{ textDecoration: "none" }}>
      <div className="pulse-dot" />
      <span>
        <strong>{activeProvider.name}</strong> Active
      </span>
      <span style={{ fontSize: "0.75rem", opacity: 0.8 }}>({activeProvider.default_model})</span>
    </Link>
  );
}
