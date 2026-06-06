import type { Metadata } from "next";
import Link from "next/link";

import "./globals.css";

export const metadata: Metadata = {
  title: "Local Music Video Studio",
  description: "Local-first AI music video production pipeline",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="container">
          <header className="row" style={{ marginBottom: 24 }}>
            <Link href="/">
              <strong>🎬 Local Music Video Studio</strong>
            </Link>
            <Link href="/projects/new" className="btn">
              New Project
            </Link>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
