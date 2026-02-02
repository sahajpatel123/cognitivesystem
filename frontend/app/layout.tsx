import "./globals.css";
import type { Metadata } from "next";
import { TopNav } from "./components/top-nav";
import { PageTransition } from "./components/page-transition";
import { SiteFooter } from "./components/site-footer";

export const metadata: Metadata = {
  title: "Cognitive System Control Surface",
  description: "Phase 5 certified human interface",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className="css-loaded-check" />
        <div className="gradient-backdrop" aria-hidden />
        <div className="site-shell">
          <TopNav />
          <PageTransition>{children}</PageTransition>
          <SiteFooter />
        </div>
      </body>
    </html>
  );
}
