"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { clearToken, isAuthenticated } from "@/lib/auth";

export function AuthControls() {
  const router = useRouter();
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    setAuthed(isAuthenticated());
  }, []);

  if (!authed) {
    return (
      <Link href="/login" className="btn secondary">
        Log in
      </Link>
    );
  }

  return (
    <div style={{ display: "flex", gap: 8 }}>
      <Link href="/projects/new" className="btn">
        New Project
      </Link>
      <button
        className="btn secondary"
        onClick={() => {
          clearToken();
          router.push("/login");
        }}
      >
        Log out
      </button>
    </div>
  );
}
