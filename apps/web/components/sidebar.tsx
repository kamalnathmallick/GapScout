"use client";

import React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Compass,
  Plus,
  Users,
  Brain,
  Settings as SettingsIcon,
  LogOut,
  Moon,
  Sun,
  ChevronLeft,
  ChevronRight,
  MapPin,
  Building2,
  Sparkles,
} from "lucide-react";
import { api } from "@/lib/api";
import { useTheme } from "./theme-provider";

interface SidebarProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

export function Sidebar({ collapsed, onToggleCollapse, mobileOpen, onCloseMobile }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { theme, toggleTheme } = useTheme();

  const handleLogout = () => {
    api.clearAuth();
    router.push("/login");
  };

  const navLinks = [
    {
      href: "/dashboard",
      label: "Dashboard",
      icon: Compass,
      match: (path: string) => path === "/" || path === "/dashboard",
    },
    {
      href: "/jobs/new",
      label: "New Analysis",
      icon: Plus,
      match: (path: string) => path.startsWith("/jobs/new"),
    },
    {
      href: "/leads",
      label: "Leads",
      icon: Users,
      match: (path: string) => path === "/leads",
    },
    {
      href: "/leads/active-learning",
      label: "Active Learning",
      icon: Sparkles,
      match: (path: string) => path.startsWith("/leads/active-learning"),
    },
    {
      href: "/models",
      label: "Model Insights",
      icon: Brain,
      match: (path: string) => path.startsWith("/models"),
    },
    {
      href: "/settings",
      label: "Settings",
      icon: SettingsIcon,
      match: (path: string) => path.startsWith("/settings"),
    },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden transition-opacity"
          aria-hidden="true"
        />
      )}

      {/* Sidebar Panel */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex flex-col bg-[#0b0f19] border-r border-slate-800/80 text-slate-300 transition-all duration-300 ease-in-out lg:static ${
          collapsed ? "w-16" : "w-60"
        } ${mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}`}
      >
        {/* Brand Header */}
        <div className="h-14 flex items-center justify-between px-3.5 border-b border-slate-800/80">
          <Link
            href="/dashboard"
            onClick={onCloseMobile}
            className="flex items-center gap-2.5 overflow-hidden group"
          >
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-600 to-indigo-400 flex items-center justify-center text-white shadow-md shadow-indigo-500/20 flex-shrink-0 group-hover:scale-105 transition-transform">
              <MapPin className="w-4 h-4" />
            </div>
            {!collapsed && (
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm tracking-tight text-white">GapScout</span>
                <span className="text-[10px] uppercase font-mono font-bold tracking-wider px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  BETA
                </span>
              </div>
            )}
          </Link>
          <button
            onClick={onToggleCollapse}
            className="hidden lg:flex p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Workspace Badge */}
        {!collapsed && (
          <div className="px-3 pt-3 pb-1">
            <div className="flex items-center justify-between px-2.5 py-1.5 rounded-lg bg-slate-900/60 border border-slate-800/60 text-xs">
              <div className="flex items-center gap-2 truncate">
                <Building2 className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
                <span className="truncate text-slate-300 font-medium">Default Workspace</span>
              </div>
              <span className="w-2 h-2 rounded-full bg-emerald-500" title="Active workspace" />
            </div>
          </div>
        )}

        {/* Navigation Links */}
        <nav className="flex-1 px-2.5 py-3 space-y-1 overflow-y-auto">
          {navLinks.map((link) => {
            const Icon = link.icon;
            const isActive = link.match(pathname);
            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={onCloseMobile}
                title={collapsed ? link.label : undefined}
                className={`flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-medium transition-all group relative ${
                  isActive
                    ? "bg-indigo-600/15 text-indigo-300 font-semibold border border-indigo-500/25"
                    : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/60 border border-transparent"
                }`}
              >
                {isActive && (
                  <span className="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r bg-indigo-500" />
                )}
                <Icon
                  className={`w-4 h-4 flex-shrink-0 transition-colors ${
                    isActive ? "text-indigo-400" : "text-slate-400 group-hover:text-slate-200"
                  }`}
                />
                {!collapsed && <span className="truncate">{link.label}</span>}
              </Link>
            );
          })}
        </nav>

        {/* Bottom Actions */}
        <div className="p-2.5 border-t border-slate-800/80 space-y-1">
          {/* Light / Dark Mode Toggle */}
          <button
            suppressHydrationWarning
            onClick={toggleTheme}
            title={theme === "dark" ? "Switch to Light mode" : "Switch to Dark mode"}
            className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs text-slate-400 hover:text-white hover:bg-slate-800/60 transition-colors"
          >
            {theme === "dark" ? (
              <Sun className="w-4 h-4 text-amber-400 flex-shrink-0" />
            ) : (
              <Moon className="w-4 h-4 text-indigo-400 flex-shrink-0" />
            )}
            {!collapsed && (
              <span className="truncate">{theme === "dark" ? "Light Mode" : "Dark Mode"}</span>
            )}
          </button>

          {/* Logout Button */}
          <button
            onClick={handleLogout}
            title="Sign out of GapScout"
            className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs text-slate-400 hover:text-rose-300 hover:bg-rose-500/10 transition-colors"
          >
            <LogOut className="w-4 h-4 flex-shrink-0" />
            {!collapsed && <span className="truncate">Sign Out</span>}
          </button>
        </div>
      </aside>
    </>
  );
}
