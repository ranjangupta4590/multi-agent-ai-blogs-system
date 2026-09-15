"use client";

import { useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";

export default function RequireAuth({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem("token")) {
      router.replace("/login");
      return;
    }
    setReady(true);
  }, [router]);

  if (!ready) {
    return (
      <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", color: "var(--text-muted)" }}>
        Checking your secure session…
      </main>
    );
  }

  return <>{children}</>;
}
