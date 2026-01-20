/* eslint-disable @next/next/no-html-link-for-pages */
"use client";
import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="site-footer" aria-label="Legal links">
      <div className="site-footer__inner">
        <span className="site-footer__brand">Cognitive System</span>
        <div className="site-footer__links">
          <Link href="/terms">Terms</Link>
          <Link href="/privacy">Privacy</Link>
          <Link href="/acceptable-use">Acceptable Use</Link>
        </div>
      </div>
      <style jsx>{`
        .site-footer {
          border-top: 1px solid #1f2937;
          padding: 16px;
          background: #030712;
          color: #9ca3af;
        }
        .site-footer__inner {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
        }
        .site-footer__links {
          display: flex;
          gap: 12px;
        }
        .site-footer__links a {
          color: #cbd5e1;
          text-decoration: none;
        }
        .site-footer__links a:hover {
          text-decoration: underline;
        }
        .site-footer__brand {
          font-weight: 600;
        }
      `}</style>
    </footer>
  );
}
