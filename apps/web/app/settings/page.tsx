"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Settings as SettingsIcon,
  Download,
  Trash2,
  User,
  Shield,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Sparkles,
  Sliders,
  DollarSign,
  Save,
  FileSpreadsheet,
} from "lucide-react";
import { api } from "@/lib/api";
import { UserOut, OfferProfileOut, WorkspaceCapsOut, ApiUsageOut } from "@/lib/types";

export default function SettingsPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"offer" | "weights" | "caps" | "usage" | "account">(
    "offer",
  );

  const [user, setUser] = useState<UserOut | null>(null);
  const [offer, setOffer] = useState<OfferProfileOut | null>(null);
  const [weights, setWeights] = useState<Record<string, number>>({
    pain: 25,
    fit: 25,
    timing: 15,
    reachability: 20,
    evidence: 15,
  });
  const [caps, setCaps] = useState<WorkspaceCapsOut>({
    max_cells_per_job: 250,
    max_places_per_job: 5000,
    daily_llm_cost_cap_usd: 2.0,
    data_retention_days: 90,
  });
  const [usage, setUsage] = useState<ApiUsageOut | null>(null);

  // Status & action states
  const [saving, setSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Account tools states
  const [isExporting, setIsExporting] = useState<string | null>(null);
  const [confirmDeleteText, setConfirmDeleteText] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const [devLink, setDevLink] = useState<string | null>(null);

  const showSuccess = (msg: string) => {
    setSuccessMessage(msg);
    setTimeout(() => setSuccessMessage(null), 4000);
  };

  useEffect(() => {
    let ignore = false;
    async function loadData() {
      try {
        const [meData, offerData, weightsData, capsData, usageData] = await Promise.all([
          api.getMe().catch(() => null),
          api.getOfferProfile().catch(() => null),
          api.getScoringWeights().catch(() => null),
          api.getWorkspaceCaps().catch(() => null),
          api.getApiUsage().catch(() => null),
        ]);

        if (!ignore) {
          if (meData) setUser(meData);
          if (offerData) setOffer(offerData);
          if (weightsData) {
            setWeights(weightsData.weights);
          }
          if (capsData) setCaps(capsData);
          if (usageData) setUsage(usageData);
        }
      } catch (err: unknown) {
        if (!ignore) {
          setErrorMessage(err instanceof Error ? err.message : "Failed to load settings data");
        }
      }
    }
    void loadData();
    return () => {
      ignore = true;
    };
  }, []);

  // Handlers
  const handleSaveOffer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!offer) return;
    setSaving(true);
    setErrorMessage(null);
    try {
      const updated = await api.updateOfferProfile({
        name: offer.name,
        target_categories: offer.target_categories,
        offer_description: offer.offer_description ?? undefined,
        min_rating: offer.min_rating ?? undefined,
        max_rating: offer.max_rating ?? undefined,
        target_regions: offer.target_regions,
      });
      setOffer(updated);
      showSuccess("Offer Profile updated successfully.");
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to save offer profile");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveWeights = async () => {
    setSaving(true);
    setErrorMessage(null);
    try {
      const updated = await api.updateScoringWeights(weights);
      setWeights(updated.weights);
      showSuccess("Custom scoring weights applied successfully.");
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to save weights");
    } finally {
      setSaving(false);
    }
  };

  const handleResetWeights = async () => {
    setSaving(true);
    setErrorMessage(null);
    try {
      const reset = await api.resetScoringWeights();
      setWeights(reset.weights);
      showSuccess("Scoring weights reset to global defaults.");
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to reset weights");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveCaps = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setErrorMessage(null);
    try {
      const updated = await api.updateWorkspaceCaps(caps);
      setCaps(updated);
      showSuccess("Workspace execution caps saved.");
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to save caps");
    } finally {
      setSaving(false);
    }
  };

  const handleExport = async (format: "json" | "csv") => {
    setIsExporting(format);
    setErrorMessage(null);
    try {
      const res = await api.exportAccountData(format);
      const blob =
        res instanceof Blob
          ? res
          : new Blob([JSON.stringify(res, null, 2)], { type: "application/json" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `gapscout-account-export-${new Date().toISOString().slice(0, 10)}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      showSuccess(`Account data exported as ${format.toUpperCase()}.`);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Export failed");
    } finally {
      setIsExporting(null);
    }
  };

  const handleDeleteAccount = async () => {
    if (confirmDeleteText !== "DELETE") {
      setErrorMessage("Please type 'DELETE' exactly to confirm deletion.");
      return;
    }
    setIsDeleting(true);
    setErrorMessage(null);
    try {
      await api.deleteAccountData();
      api.clearAuth();
      router.push("/login");
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Account deletion failed");
      setIsDeleting(false);
    }
  };

  const handleVerifyEmail = async () => {
    setSaving(true);
    try {
      const res = await api.requestEmailVerification();
      if (res.dev_link) {
        setDevLink(res.dev_link);
      }
      showSuccess(res.message);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Email verification failed");
    } finally {
      setSaving(false);
    }
  };

  const handlePasswordReset = async () => {
    if (!user?.email) return;
    setSaving(true);
    try {
      const res = await api.forgotPassword(user.email);
      if (res.dev_link) {
        setDevLink(res.dev_link);
      }
      showSuccess(res.message);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Password reset failed");
    } finally {
      setSaving(false);
    }
  };

  const totalWeight = Object.values(weights).reduce((a, b) => a + b, 0);

  return (
    <div className="flex-1 p-6 sm:p-8 max-w-6xl mx-auto w-full space-y-6">
      {/* Header */}
      <div className="pb-6 border-b border-slate-800/80">
        <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
          <SettingsIcon className="w-6 h-6 text-indigo-400" />
          <span>Workspace &amp; Account Settings</span>
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Configure offer target criteria, lead scoring weights, execution safety caps, API budget,
          and privacy data exports.
        </p>
      </div>

      {/* Notifications */}
      {successMessage && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {errorMessage && (
        <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {devLink && (
        <div className="p-3.5 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs flex items-center justify-between gap-2 font-mono">
          <span className="truncate">DEV LINK: {devLink}</span>
          <a
            href={devLink}
            target="_blank"
            rel="noreferrer"
            className="text-white bg-indigo-600 px-2 py-1 rounded text-[11px] font-semibold whitespace-nowrap hover:bg-indigo-500"
          >
            Open Link
          </a>
        </div>
      )}

      {/* 2-Column Vertical Tabs Layout */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Navigation Sidebar */}
        <div className="md:col-span-1 space-y-1">
          {[
            { id: "offer", label: "Offer Profile", icon: Sparkles },
            { id: "weights", label: "Scoring Weights", icon: Sliders },
            { id: "caps", label: "Workspace Caps", icon: Shield },
            { id: "usage", label: "API Usage", icon: DollarSign },
            { id: "account", label: "Account & Privacy", icon: User },
          ].map((tab) => {
            const Icon = tab.icon;
            const isSelected = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-semibold text-left transition-colors ${
                  isSelected
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-400 hover:text-white hover:bg-slate-800/60"
                }`}
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Content Panel (Right 3 cols) */}
        <div className="md:col-span-3">
          {/* Tab 1: Offer Profile */}
          {activeTab === "offer" && (
            <div className="glass-panel rounded-2xl p-6 border border-slate-800/80 space-y-6">
              <div>
                <h2 className="text-base font-bold text-white">Offer Profile</h2>
                <p className="text-xs text-slate-400 mt-1">
                  Define what service you provide and which businesses are ideal commercial fits.
                </p>
              </div>

              <form onSubmit={handleSaveOffer} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5 font-mono">
                    Profile Name
                  </label>
                  <input
                    type="text"
                    required
                    value={offer?.name || ""}
                    onChange={(e) =>
                      setOffer((prev) => (prev ? { ...prev, name: e.target.value } : null))
                    }
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5 font-mono">
                    Offer Value Proposition
                  </label>
                  <textarea
                    rows={3}
                    value={offer?.offer_description || ""}
                    onChange={(e) =>
                      setOffer((prev) =>
                        prev ? { ...prev, offer_description: e.target.value } : null,
                      )
                    }
                    placeholder="e.g. Turn slow weekday mornings into loyal subscription revenue with hyper-local SEO and geo-targeted ads."
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5 font-mono">
                    Target Categories (comma separated)
                  </label>
                  <input
                    type="text"
                    value={offer?.target_categories?.join(", ") || ""}
                    onChange={(e) =>
                      setOffer((prev) =>
                        prev
                          ? {
                              ...prev,
                              target_categories: e.target.value
                                .split(",")
                                .map((s) => s.trim())
                                .filter(Boolean),
                            }
                          : null,
                      )
                    }
                    placeholder="cafe, restaurant, gym"
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div className="pt-2">
                  <button
                    type="submit"
                    disabled={saving}
                    className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center gap-2 transition-colors shadow-sm"
                  >
                    <Save className="w-3.5 h-3.5" />
                    <span>Save Offer Profile</span>
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Tab 2: Scoring Weights */}
          {activeTab === "weights" && (
            <div className="glass-panel rounded-2xl p-6 border border-slate-800/80 space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-base font-bold text-white">Lead Scoring Formula Editor</h2>
                  <p className="text-xs text-slate-400 mt-1">
                    Calibrate the 5 deterministic scoring pillars to align with your agency’s sales
                    strategy.
                  </p>
                </div>
                <button
                  onClick={handleResetWeights}
                  disabled={saving}
                  className="px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs font-semibold flex items-center gap-1.5 transition-colors self-start sm:self-auto"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Reset to Defaults</span>
                </button>
              </div>

              {/* Live Sum Indicator */}
              <div
                className={`p-3 rounded-xl border flex items-center justify-between text-xs font-mono ${
                  totalWeight === 100
                    ? "bg-emerald-500/10 border-emerald-500/25 text-emerald-300"
                    : "bg-amber-500/10 border-amber-500/25 text-amber-300"
                }`}
              >
                <span>Total Formula Weight:</span>
                <span className="font-bold tabular-nums">{totalWeight} / 100 pts</span>
              </div>

              <div className="space-y-4">
                {Object.entries(weights).map(([key, val]) => (
                  <div key={key} className="space-y-1.5">
                    <div className="flex justify-between text-xs">
                      <span className="capitalize font-semibold text-slate-200">{key}</span>
                      <span className="font-mono text-indigo-400 font-bold tabular-nums">
                        {val} pts
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="50"
                      step="5"
                      value={val}
                      onChange={(e) =>
                        setWeights((prev) => ({ ...prev, [key]: Number(e.target.value) }))
                      }
                      className="w-full accent-indigo-500 cursor-pointer"
                    />
                  </div>
                ))}
              </div>

              <div className="pt-2">
                <button
                  onClick={handleSaveWeights}
                  disabled={saving || totalWeight !== 100}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center gap-2 transition-colors shadow-sm"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>Save Scoring Formula</span>
                </button>
              </div>
            </div>
          )}

          {/* Tab 3: Workspace Caps */}
          {activeTab === "caps" && (
            <div className="glass-panel rounded-2xl p-6 border border-slate-800/80 space-y-6">
              <div>
                <h2 className="text-base font-bold text-white">
                  Execution Caps &amp; Data Retention
                </h2>
                <p className="text-xs text-slate-400 mt-1">
                  Enforce strict execution boundaries to prevent runaway scraping costs or memory
                  bloat.
                </p>
              </div>

              <form onSubmit={handleSaveCaps} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5 font-mono">
                      Max Places Per Job
                    </label>
                    <input
                      type="number"
                      value={caps.max_places_per_job}
                      onChange={(e) =>
                        setCaps((prev) => ({ ...prev, max_places_per_job: Number(e.target.value) }))
                      }
                      className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs font-mono tabular-nums focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5 font-mono">
                      Max Cells Per Job
                    </label>
                    <input
                      type="number"
                      value={caps.max_cells_per_job}
                      onChange={(e) =>
                        setCaps((prev) => ({ ...prev, max_cells_per_job: Number(e.target.value) }))
                      }
                      className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs font-mono tabular-nums focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5 font-mono">
                      Daily LLM Cost Cap ($ USD)
                    </label>
                    <input
                      type="number"
                      step="0.5"
                      value={caps.daily_llm_cost_cap_usd}
                      onChange={(e) =>
                        setCaps((prev) => ({
                          ...prev,
                          daily_llm_cost_cap_usd: Number(e.target.value),
                        }))
                      }
                      className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs font-mono tabular-nums focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5 font-mono">
                      Raw Data Retention (Days)
                    </label>
                    <input
                      type="number"
                      value={caps.data_retention_days}
                      onChange={(e) =>
                        setCaps((prev) => ({
                          ...prev,
                          data_retention_days: Number(e.target.value),
                        }))
                      }
                      className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs font-mono tabular-nums focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>

                <div className="pt-2">
                  <button
                    type="submit"
                    disabled={saving}
                    className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center gap-2 transition-colors shadow-sm"
                  >
                    <Save className="w-3.5 h-3.5" />
                    <span>Save Execution Caps</span>
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Tab 4: API Usage */}
          {activeTab === "usage" && (
            <div className="glass-panel rounded-2xl p-6 border border-slate-800/80 space-y-6">
              <div>
                <h2 className="text-base font-bold text-white">API Usage &amp; Cost Metering</h2>
                <p className="text-xs text-slate-400 mt-1">
                  Track real-time token consumption, LLM calls, and daily budget exhaustion.
                </p>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="bg-slate-950/80 p-3.5 rounded-xl border border-slate-800">
                  <span className="text-[11px] text-slate-500 block mb-1 font-mono">
                    TODAY COST
                  </span>
                  <span className="text-lg font-bold font-mono text-emerald-400 tabular-nums">
                    ${usage?.cost_today_usd?.toFixed(2) ?? "0.00"}
                  </span>
                </div>

                <div className="bg-slate-950/80 p-3.5 rounded-xl border border-slate-800">
                  <span className="text-[11px] text-slate-500 block mb-1 font-mono">DAILY CAP</span>
                  <span className="text-lg font-bold font-mono text-white tabular-nums">
                    ${usage?.daily_cost_cap_usd?.toFixed(2) ?? "2.00"}
                  </span>
                </div>

                <div className="bg-slate-950/80 p-3.5 rounded-xl border border-slate-800">
                  <span className="text-[11px] text-slate-500 block mb-1 font-mono">REMAINING</span>
                  <span className="text-lg font-bold font-mono text-indigo-400 tabular-nums">
                    ${usage?.remaining_budget_today_usd?.toFixed(2) ?? "2.00"}
                  </span>
                </div>

                <div className="bg-slate-950/80 p-3.5 rounded-xl border border-slate-800">
                  <span className="text-[11px] text-slate-500 block mb-1 font-mono">
                    TOTAL CALLS
                  </span>
                  <span className="text-lg font-bold font-mono text-white tabular-nums">
                    {usage?.total_calls ?? 0}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Tab 5: Account & Privacy */}
          {activeTab === "account" && (
            <div className="space-y-6">
              {/* Account Details */}
              <div className="glass-panel rounded-2xl p-6 border border-slate-800/80 space-y-4">
                <h2 className="text-base font-bold text-white">Account Information</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                  <div>
                    <span className="text-slate-500 block text-[11px] font-mono">USER EMAIL</span>
                    <span className="font-mono text-slate-200">{user?.email || "--"}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[11px] font-mono">
                      WORKSPACE ROLE
                    </span>
                    <span className="font-mono text-indigo-400 font-bold uppercase">
                      {user?.role || "Owner"}
                    </span>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2 pt-2">
                  <button
                    onClick={handleVerifyEmail}
                    disabled={saving || user?.is_verified}
                    className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs font-semibold text-slate-300 transition-colors disabled:opacity-50"
                  >
                    {user?.is_verified ? "Email Verified ✓" : "Verify Email"}
                  </button>
                  <button
                    onClick={handlePasswordReset}
                    disabled={saving}
                    className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs font-semibold text-slate-300 transition-colors"
                  >
                    Reset Password
                  </button>
                </div>
              </div>

              {/* Privacy & Data Export */}
              <div className="glass-panel rounded-2xl p-6 border border-slate-800/80 space-y-4">
                <h2 className="text-base font-bold text-white">Data Export &amp; Portability</h2>
                <p className="text-xs text-slate-400">
                  Export all your search jobs, H3 hex calculations, and leads in standard formats.
                </p>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => handleExport("json")}
                    disabled={isExporting !== null}
                    className="px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-200 text-xs font-semibold flex items-center gap-1.5 transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Export JSON</span>
                  </button>
                  <button
                    onClick={() => handleExport("csv")}
                    disabled={isExporting !== null}
                    className="px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-200 text-xs font-semibold flex items-center gap-1.5 transition-colors"
                  >
                    <FileSpreadsheet className="w-3.5 h-3.5" />
                    <span>Export CSV</span>
                  </button>
                </div>
              </div>

              {/* Danger Zone */}
              <div className="glass-panel rounded-2xl p-6 border border-rose-500/30 bg-rose-950/10 space-y-4">
                <div className="flex items-center gap-2 text-rose-400">
                  <Trash2 className="w-4 h-4" />
                  <h2 className="text-base font-bold text-white">Danger Zone: Delete All Data</h2>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Irreversibly delete your account, workspace, search jobs, hex metrics, and
                  outreach leads. This action cannot be undone.
                </p>
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                  <input
                    type="text"
                    value={confirmDeleteText}
                    onChange={(e) => setConfirmDeleteText(e.target.value)}
                    placeholder="Type DELETE to confirm"
                    className="px-3 py-1.5 rounded-lg bg-slate-950 border border-rose-500/40 text-rose-200 text-xs font-mono focus:outline-none"
                  />
                  <button
                    onClick={handleDeleteAccount}
                    disabled={isDeleting || confirmDeleteText !== "DELETE"}
                    className="px-3.5 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 disabled:opacity-40 text-white text-xs font-semibold transition-colors"
                  >
                    {isDeleting ? "Deleting..." : "Permanently Delete Account"}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
