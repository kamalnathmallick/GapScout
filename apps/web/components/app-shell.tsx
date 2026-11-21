"use client";

import React, { useState, useEffect, useSyncExternalStore } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { Loader2 } from "lucide-react";

function subscribeAuth(callback: () => void) {
  window.addEventListener("storage", callback);
  return () => window.removeEventListener("storage", callback);
}

function getAuthSnapshot(): boolean {
  if (typeof window === "undefined") return true;
  return !!localStorage.getItem("gapscout_access_token");
}

function getServerAuthSnapshot(): boolean {
  return true;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  // Auth & public pages
  const isAuthPage = pathname === "/login" || pathname === "/register";
  const isPublicPage = isAuthPage || pathname === "/";

  const hasToken = useSyncExternalStore(subscribeAuth, getAuthSnapshot, getServerAuthSnapshot);

  useEffect(() => {
    if (!isPublicPage && !hasToken) {
      router.replace(`/login?redirect=${encodeURIComponent(pathname)}`);
    }
  }, [isPublicPage, hasToken, pathname, router]);

  if (isAuthPage) {
    return <main className="min-h-screen flex flex-col justify-center">{children}</main>;
  }

  // Show a sleek loading state while redirecting unauthenticated users
  if (!isPublicPage && !hasToken) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#090d16] text-slate-400">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
          <span className="text-xs font-mono">Redirecting to sign in...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex bg-[#090d16] text-slate-100 antialiased font-sans">
      {/* Sidebar */}
      <Sidebar
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed(!collapsed)}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-x-hidden">
        <Header onToggleMobile={() => setMobileOpen(true)} />
        <main className="flex-1 flex flex-col min-w-0">{children}</main>
      </div>
    </div>
  );
}
