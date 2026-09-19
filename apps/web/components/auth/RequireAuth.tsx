"use client";

import { useRouter } from "next/navigation";
import { ReactNode, useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import SubscriptionBarrier from "./SubscriptionBarrier";

export default function RequireAuth({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [barrierError, setBarrierError] = useState<string | null>(null);

  const verifyWorkspaceAccess = useCallback(async () => {
    if (!localStorage.getItem("token")) {
      router.replace("/login");
      return;
    }
    try {
      const user = await api.getMe();
      if (user.role === "PUBLIC_USER") {
        router.replace("/admin-signup");
        return;
      }
      setBarrierError(null);
      setReady(true);
    } catch (err: any) {
      const msg = err.message || "";
      if (
        msg.toLowerCase().includes("subscription expired") ||
        msg.toLowerCase().includes("workspace blocked") ||
        msg.toLowerCase().includes("frozen by")
      ) {
        setBarrierError(msg);
        setReady(true);
      } else {
        localStorage.removeItem("token");
        router.replace("/login");
      }
    }
  }, [router]);

  useEffect(() => {
    verifyWorkspaceAccess();
  }, [verifyWorkspaceAccess]);

  if (!ready) {
    return (
      <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", color: "var(--text-muted)" }}>
        Checking your secure session…
      </main>
    );
  }

  if (barrierError) {
    return (
      <SubscriptionBarrier
        errorMessage={barrierError}
        onRenewed={() => {
          setBarrierError(null);
          verifyWorkspaceAccess();
        }}
      />
    );
  }

  return <>{children}</>;
}
