"use client";

import { useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function RequireAuth({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const verifyWorkspaceAccess = async () => {
      if (!localStorage.getItem("token")) { router.replace("/login"); return; }
      try {
        const user = await api.getMe();
        if (user.role === "PUBLIC_USER") { router.replace("/"); return; }
        setReady(true);
      } catch {
        localStorage.removeItem("token");
        router.replace("/login");
      }
    };
    verifyWorkspaceAccess();
  }, [router]);

  if (!ready) return <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", color: "var(--text-muted)" }}>Checking your secure session…</main>;
  return <>{children}</>;
}
