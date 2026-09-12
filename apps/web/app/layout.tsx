import "@/styles/globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Antigravity | Multi-Agent AI Blog Generation Platform",
  description: "Enterprise-grade multi-agent autonomous blog writing platform with single-provider independence and rigorous source grounding.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" data-theme="dark">
      <body>{children}</body>
    </html>
  );
}
