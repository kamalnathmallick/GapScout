"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, Plus, ChevronRight } from "lucide-react";
import { api } from "@/lib/api";

interface HeaderProps {
  onToggleMobile: () => void;
}

export function Header({ onToggleMobile }: HeaderProps) {
  const pathname = usePathname();
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let active = true;
    async function checkHealth() {
      try {
        const res = await api.getHealth();
        if (active) {
          setApiOnline(res.status === "ok");
        }
      } catch {
        if (active) {
          setApiOnline(false);
        }
      }
    }
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  const getBreadcrumb = () => {
    if (pathname === "/" || pathname === "/dashboard") return "Dashboard";
    if (pathname.startsWith("/jobs/new")) return "New Analysis";
    if (pathname.startsWith("/jobs/")) return "Analysis Progress";
    if (pathname.startsWith("/gap/")) return "Interactive Gap Map";
    if (pathname === "/leads") return "Leads Pipeline";
    if (pathname.startsWith("/leads/active-learning")) return "Active Learning";
    if (pathname.startsWith("/models")) return "Model Insights";
    if (pathname.startsWith("/settings")) return "Settings";
    return "Workspace";
  };

  return (
    <header className="h-14 border-b border-slate-800/80 bg-[#0b0f19]/90 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between sticky top-0 z-30">
      {/* Left: Mobile Toggle + Breadcrumbs */}
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleMobile}
          className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          aria-label="Toggle navigation drawer"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-1.5 text-xs">
          <Link
            href="/dashboard"
            className="text-slate-400 hover:text-slate-200 transition-colors font-medium"
          >
            GapScout
          </Link>
          <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
          <span className="font-semibold text-slate-100">{getBreadcrumb()}</span>
        </div>
      </div>

      {/* Right: Health Dot + New Analysis CTA */}
      <div className="flex items-center gap-3">
        {/* Backend health dot */}
        <div
          className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-full bg-slate-900/80 border border-slate-800 text-[11px] text-slate-400"
          title={
            apiOnline === null
              ? "Checking API status..."
              : apiOnline
                ? "FastAPI & Redis connected"
                : "API unreachable"
          }
        >
          <span
            className={`w-2 h-2 rounded-full ${
              apiOnline === null
                ? "bg-amber-400 animate-pulse"
                : apiOnline
                  ? "bg-emerald-400 animate-pulse-subtle"
                  : "bg-rose-500"
            }`}
          />
          <span className="font-mono text-slate-300">
            {apiOnline === null ? "Connecting..." : apiOnline ? "API Online" : "API Offline"}
          </span>
        </div>

        {/* New Analysis CTA */}
        <Link
          href="/jobs/new"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-sm shadow-indigo-600/30 transition-all hover:scale-[1.02]"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New Analysis</span>
        </Link>
      </div>
    </header>
  );
}
