import type { Metadata } from "next";
import { Caprasimo, Figtree } from "next/font/google";
import Link from "next/link";
import Nav from "@/components/Nav";
import { data } from "@/lib/data";
import "./globals.css";

const heading = Caprasimo({
  weight: "400",
  subsets: ["latin"],
  display: "swap",
  variable: "--font-heading-next",
});

const body = Figtree({
  weight: ["400", "600", "700"],
  subsets: ["latin"],
  display: "swap",
  variable: "--font-body-next",
});

export const metadata: Metadata = {
  title: "Buggy — a benchmark for tests",
  description:
    "Seventeen planted defects, four competing test suites, and a record of who noticed.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${heading.variable} ${body.variable}`}>
      <body>
        <header className="topbar">
          <div className="topbar-inner">
            <Link href="/" className="brand">
              <span className="brand-mark" aria-hidden />
              <span className="brand-name">{data.projectName}</span>
              <span className="brand-sub">a benchmark for tests</span>
            </Link>
            <Nav />
          </div>
        </header>

        <main>{children}</main>

        <footer className="footer">
          <div className="footer-inner">
            <span className="brand-name">{data.projectName}</span>
            <span style={{ flex: 1 }} />
            <span className="muted" style={{ fontSize: "13.5px" }}>
              A planted defect is a mutant. Mutation testing, inverted to grade
              the tests.
            </span>
          </div>
        </footer>
      </body>
    </html>
  );
}
