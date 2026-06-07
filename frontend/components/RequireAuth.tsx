"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { isAuthenticated } from "@/lib/auth";

/** Sends unauthenticated visitors to /login (except on the login page itself). */
export function RequireAuth() {
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (pathname !== "/login" && !isAuthenticated()) {
      router.replace("/login");
    }
  }, [pathname, router]);

  return null;
}
