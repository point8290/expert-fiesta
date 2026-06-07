import type { Metadata } from "next";
import Link from "next/link";

import { AuthControls } from "@/components/AuthControls";
import { RequireAuth } from "@/components/RequireAuth";

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
        <RequireAuth />
        <div className="container">
          <header className="row" style={{ marginBottom: 24 }}>
            <Link href="/">
              <strong>🎬 Local Music Video Studio</strong>
            </Link>
            <AuthControls />
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
