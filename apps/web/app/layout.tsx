import "@/styles/globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "BlogPilot | Multi-Agent AI Blog Generation Platform",
  description: "Enterprise-grade multi-agent autonomous blog writing platform with single-provider independence and rigorous source grounding.",
};

const SocialIcon = ({ children }: { children: React.ReactNode }) => <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">{children}</svg>;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="light">
      <body>
        {children}
        <footer className="site-footer">
          <div className="footer-brand"><span>✦</span><strong>BlogPilot</strong></div>
          <div className="footer-credit">Made with <span aria-label="love" role="img">♥</span> by Ranjan Gupta <i>·</i> © 2026</div>
          <nav className="footer-socials" aria-label="Social links">
            <a href="https://github.com/ranjangupta4590/multi-agent-ai-blogs-system/" target="_blank" rel="noreferrer" aria-label="GitHub" title="GitHub"><SocialIcon><path fill="currentColor" d="M12 2a10 10 0 0 0-3.16 19.49c.5.09.68-.22.68-.48v-1.7c-2.78.61-3.37-1.18-3.37-1.18-.45-1.15-1.11-1.46-1.11-1.46-.91-.62.07-.61.07-.61 1 .07 1.54 1.04 1.54 1.04.9 1.53 2.34 1.09 2.91.83.09-.65.35-1.09.64-1.34-2.22-.25-4.56-1.11-4.56-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.65 0 0 .84-.27 2.75 1.03A9.55 9.55 0 0 1 12 6.8c.85 0 1.7.11 2.5.34 1.91-1.3 2.75-1.03 2.75-1.03.55 1.38.2 2.4.1 2.65.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.68-4.57 4.93.36.31.68.9.68 1.82v2.7c0 .27.18.58.69.48A10 10 0 0 0 12 2Z" /></SocialIcon></a>
            <a href="https://www.linkedin.com" target="_blank" rel="noreferrer" aria-label="LinkedIn" title="LinkedIn"><SocialIcon><path fill="currentColor" d="M4.98 3.5C4.98 4.88 3.87 6 2.5 6S0 4.88 0 3.5 1.12 1 2.5 1 5 2.12 5 3.5H4.98ZM.28 8.2H4.7V23H.28V8.2ZM7.45 8.2h4.23v2.02h.06c.59-1.12 2.03-2.3 4.18-2.3 4.47 0 5.3 2.94 5.3 6.76V23h-4.4v-7.32c0-1.75-.04-4-2.45-4-2.45 0-2.82 1.91-2.82 3.87V23H7.15V8.2h.3Z" /></SocialIcon></a>
            <a href="https://x.com" target="_blank" rel="noreferrer" aria-label="X" title="X"><SocialIcon><path fill="currentColor" d="M18.9 2H22l-6.77 7.74L23.2 22h-6.24l-4.89-7.37L5.62 22H2.5l7.24-8.27L2.1 2h6.4l4.42 6.72L18.9 2Zm-1.1 18h1.73L7.56 3.9H5.7L17.8 20Z" /></SocialIcon></a>
            <a href="https://www.instagram.com" target="_blank" rel="noreferrer" aria-label="Instagram" title="Instagram"><SocialIcon><path fill="currentColor" d="M7 2h10a5 5 0 0 1 5 5v10a5 5 0 0 1-5 5H7a5 5 0 0 1-5-5V7a5 5 0 0 1 5-5Zm0 2a3 3 0 0 0-3 3v10a3 3 0 0 0 3 3h10a3 3 0 0 0 3-3V7a3 3 0 0 0-3-3H7Zm5 3.5A4.5 4.5 0 1 1 7.5 12 4.5 4.5 0 0 1 12 7.5Zm0 2A2.5 2.5 0 1 0 14.5 12 2.5 2.5 0 0 0 12 9.5ZM17.8 6.4a1.2 1.2 0 1 1-1.2 1.2 1.2 1.2 0 0 1 1.2-1.2Z" /></SocialIcon></a>
            <a href="https://www.youtube.com" target="_blank" rel="noreferrer" aria-label="YouTube" title="YouTube"><SocialIcon><path fill="currentColor" d="M23.5 6.2a3 3 0 0 0-2.11-2.12C19.52 3.5 12 3.5 12 3.5s-7.52 0-9.39.58A3 3 0 0 0 .5 6.2C0 8.08 0 12 0 12s0 3.92.5 5.8a3 3 0 0 0 2.11 2.12c1.87.58 9.39.58 9.39.58s7.52 0 9.39-.58a3 3 0 0 0 2.11-2.12C24 15.92 24 12 24 12s0-3.92-.5-5.8ZM9.6 15.58V8.42L15.88 12 9.6 15.58Z" /></SocialIcon></a>
          </nav>
        </footer>
      </body>
    </html>
  );
}
