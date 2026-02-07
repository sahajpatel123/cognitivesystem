import { TopNav } from "../components/top-nav";
import { PageTransition } from "../components/page-transition";

export default function MarketingLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <>
      <TopNav />
      <PageTransition>{children}</PageTransition>
    </>
  );
}
