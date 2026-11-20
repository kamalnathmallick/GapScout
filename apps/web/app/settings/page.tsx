"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Settings as SettingsIcon,
  Download,
  Trash2,
  Building,
  User,
  Shield,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Sparkles,
  Sliders,
  DollarSign,
  Save,
  KeyRound,
  FileSpreadsheet,
} from "lucide-react";
import { api } from "@/lib/api";
import { UserOut, OfferProfileOut, WorkspaceCapsOut, ApiUsageOut } from "@/lib/types";

export default function SettingsPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"offer" | "weights" | "caps" | "usage" | "account">(
    "offer",
  );

  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<UserOut | null>(null);
  const [offer, setOffer] = useState<OfferProfileOut | null>(null);
  const [weights, setWeights] = useState<Record<string, number>>({
    pain: 25,
    fit: 25,
    timing: 15,
    reachability: 20,
    evidence: 15,
  });
  const [isCustomWeights, setIsCustomWeights] = useState(false);
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
            setIsCustomWeights(weightsData.is_custom);
          }
          if (capsData) setCaps(capsData);
          if (usageData) setUsage(usageData);
        }
      } catch (err: unknown) {
        if (!ignore) {
          setErrorMessage(err instanceof Error ? err.message : "Failed to load settings data");
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }
    void loadData();
    return () => {
      ignore = true;
    };
  }, []);

  // Handlers
  const handleSaveOffer = async () => {
    if (!offer) return;
    setSaving(true);
    try {
      const updated = await api.updateOfferProfile({
        name: offer.name,
        offer_description: offer.offer_description || undefined,
        target_categories: offer.target_categories,
        min_rating: offer.min_rating,
        max_rating: offer.max_rating,
        target_regions: offer.target_regions,
      });
      setOffer(updated);
      showSuccess("Offer Profile saved and lead scores recomputed.");
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to save offer profile");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveWeights = async () => {
    setSaving(true);
    try {
      const res = await api.updateScoringWeights(weights);
      setWeights(res.weights);
      setIsCustomWeights(res.is_custom);
      showSuccess("Lead scoring weights updated successfully.");
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to save scoring weights");
    } finally {
      setSaving(false);
    }
  };

  const handleResetWeights = async () => {
    setSaving(true);
    try {
      const res = await api.resetScoringWeights();
      setWeights(res.weights);
      setIsCustomWeights(false);
      showSuccess("Scoring weights reset to factory defaults (25/25/15/20/15).");
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to reset weights");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveCaps = async () => {
    setSaving(true);
    try {
      const res = await api.updateWorkspaceCaps(caps);
      setCaps(res);
      showSuccess("Workspace limits and retention policy saved.");
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to update workspace limits");
    } finally {
      setSaving(false);
    }
  };

  const handleExport = async (format: "json" | "csv") => {
    setIsExporting(format);
    try {
      if (format === "csv") {
        const blob = (await api.exportAccountData("csv")) as Blob;
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `gapscout-export-${user?.workspace?.name || "data"}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } else {
        const data = await api.exportAccountData("json");
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `gapscout-export-${user?.workspace?.name || "data"}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
      showSuccess(`Exported workspace data as ${format.toUpperCase()}`);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Export failed");
    } finally {
      setIsExporting(null);
    }
  };

  const handleDeleteData = async () => {
    if (confirmDeleteText !== "DELETE MY DATA") {
      setErrorMessage("Please type 'DELETE MY DATA' exactly to confirm permanent deletion.");
      return;
    }
    if (
      !window.confirm(
        "Irreversible action! This will immediately delete all search jobs, places, leads, and outreach events.",
      )
    ) {
      return;
    }
    setIsDeleting(true);
    try {
      await api.deleteAccountData("DELETE MY DATA");
      api.clearAuth();
      router.push("/login");
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Deletion failed");
      setIsDeleting(false);
    }
  };

  const handleRequestVerification = async () => {
    try {
      const res = await api.requestEmailVerification(user?.email);
      showSuccess(res.message);
      if (res.dev_link) setDevLink(res.dev_link);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Verification request failed");
    }
  };

  const handleForgotPassword = async () => {
    if (!user?.email) return;
    try {
      const res = await api.forgotPassword(user.email);
      showSuccess(res.message);
      if (res.dev_link) setDevLink(res.dev_link);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Password reset request failed");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 text-white p-6 sm:p-10 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
      </div>
    );
  }

  const totalWeight = Object.values(weights).reduce((a, b) => a + Number(b || 0), 0);

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6 sm:p-10">
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <SettingsIcon className="w-7 h-7 text-indigo-400" />
            <span>Workspace & Account Settings</span>
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Manage your offer profile, lead scoring formula, resource limits, API usage, and
            compliance data.
          </p>
        </div>

        {/* Alerts */}
        {successMessage && (
          <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-800 text-emerald-300 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{successMessage}</span>
          </div>
        )}
        {errorMessage && (
          <div className="p-4 rounded-xl bg-red-950/40 border border-red-800 text-red-300 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}
        {devLink && (
          <div className="p-4 rounded-xl bg-indigo-950/50 border border-indigo-800 text-indigo-200 text-xs space-y-1 font-mono">
            <span className="font-semibold text-indigo-300 block">Dev Link (Simulated Email):</span>
            <a
              href={devLink}
              target="_blank"
              rel="noopener noreferrer"
              className="underline break-all"
            >
              {devLink}
            </a>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="flex border-b border-gray-800 space-x-6 text-sm font-semibold overflow-x-auto">
          <button
            onClick={() => setActiveTab("offer")}
            className={`pb-3 flex items-center gap-2 border-b-2 whitespace-nowrap transition-colors ${
              activeTab === "offer"
                ? "border-indigo-500 text-indigo-400"
                : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <Sparkles className="w-4 h-4" />
            <span>Offer Profile</span>
          </button>
          <button
            onClick={() => setActiveTab("weights")}
            className={`pb-3 flex items-center gap-2 border-b-2 whitespace-nowrap transition-colors ${
              activeTab === "weights"
                ? "border-indigo-500 text-indigo-400"
                : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <Sliders className="w-4 h-4" />
            <span>Scoring Weights</span>
          </button>
          <button
            onClick={() => setActiveTab("caps")}
            className={`pb-3 flex items-center gap-2 border-b-2 whitespace-nowrap transition-colors ${
              activeTab === "caps"
                ? "border-indigo-500 text-indigo-400"
                : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <Shield className="w-4 h-4" />
            <span>Workspace Caps & Retention</span>
          </button>
          <button
            onClick={() => setActiveTab("usage")}
            className={`pb-3 flex items-center gap-2 border-b-2 whitespace-nowrap transition-colors ${
              activeTab === "usage"
                ? "border-indigo-500 text-indigo-400"
                : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <DollarSign className="w-4 h-4" />
            <span>API & LLM Usage</span>
          </button>
          <button
            onClick={() => setActiveTab("account")}
            className={`pb-3 flex items-center gap-2 border-b-2 whitespace-nowrap transition-colors ${
              activeTab === "account"
                ? "border-indigo-500 text-indigo-400"
                : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <Building className="w-4 h-4" />
            <span>Account & Data Tools</span>
          </button>
        </div>

        {/* TAB 1: OFFER PROFILE */}
        {activeTab === "offer" && (
          <div className="rounded-xl bg-gray-900 border border-gray-800 p-6 space-y-6">
            <div>
              <h2 className="text-base font-semibold text-white">
                Offer Profile & Pitch Positioning
              </h2>
              <p className="text-xs text-gray-400 mt-0.5">
                Define what service or product your agency sells. The lead scorer uses this to
                prioritize high-fit leads and personalize cold drafts.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5 md:col-span-2">
                <label className="text-xs font-medium text-gray-300">Offer Title</label>
                <input
                  type="text"
                  value={offer?.name || ""}
                  onChange={(e) =>
                    setOffer((prev) => (prev ? { ...prev, name: e.target.value } : null))
                  }
                  placeholder="e.g. Local SEO & Google Review Acceleration"
                  className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-xs text-white focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div className="space-y-1.5 md:col-span-2">
                <label className="text-xs font-medium text-gray-300">
                  Description & Value Proposition
                </label>
                <textarea
                  value={offer?.offer_description || ""}
                  onChange={(e) =>
                    setOffer((prev) =>
                      prev ? { ...prev, offer_description: e.target.value } : null,
                    )
                  }
                  placeholder="Describe your offer, guarantee, or case studies..."
                  rows={3}
                  className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-xs text-white focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-gray-300">
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
                  placeholder="restaurant, dental, salon"
                  className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-xs text-white focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-gray-300">
                  Target Regions / Cities (comma separated)
                </label>
                <input
                  type="text"
                  value={offer?.target_regions?.join(", ") || ""}
                  onChange={(e) =>
                    setOffer((prev) =>
                      prev
                        ? {
                            ...prev,
                            target_regions: e.target.value
                              .split(",")
                              .map((s) => s.trim())
                              .filter(Boolean),
                          }
                        : null,
                    )
                  }
                  placeholder="Bengaluru, Mumbai, Delhi"
                  className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-xs text-white focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-gray-300">
                  Minimum Rating Target (e.g. 3.0)
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="1"
                  max="5"
                  value={offer?.min_rating ?? ""}
                  onChange={(e) =>
                    setOffer((prev) =>
                      prev
                        ? {
                            ...prev,
                            min_rating: e.target.value ? parseFloat(e.target.value) : null,
                          }
                        : null,
                    )
                  }
                  placeholder="3.0"
                  className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-xs text-white focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-gray-300">
                  Maximum Rating Target (e.g. 4.5)
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="1"
                  max="5"
                  value={offer?.max_rating ?? ""}
                  onChange={(e) =>
                    setOffer((prev) =>
                      prev
                        ? {
                            ...prev,
                            max_rating: e.target.value ? parseFloat(e.target.value) : null,
                          }
                        : null,
                    )
                  }
                  placeholder="4.5"
                  className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-xs text-white focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            </div>

            <div className="pt-3 border-t border-gray-800 flex justify-end">
              <button
                onClick={handleSaveOffer}
                disabled={saving}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 font-semibold text-xs rounded-lg flex items-center gap-2 transition-colors"
              >
                <Save className="w-4 h-4" />
                <span>{saving ? "Saving..." : "Save Offer Profile"}</span>
              </button>
            </div>
          </div>
        )}

        {/* TAB 2: SCORING WEIGHTS */}
        {activeTab === "weights" && (
          <div className="rounded-xl bg-gray-900 border border-gray-800 p-6 space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-white">Lead Scoring Formula Editor</h2>
                <p className="text-xs text-gray-400 mt-0.5">
                  Tune the weight of each component in the 0-100 cold-start lead scorer. Factory
                  default: 25 / 25 / 15 / 20 / 15.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`text-xs font-mono font-semibold px-2.5 py-1 rounded-md ${
                    totalWeight === 100
                      ? "bg-emerald-950 border border-emerald-800 text-emerald-300"
                      : "bg-amber-950 border border-amber-800 text-amber-300"
                  }`}
                >
                  Total: {totalWeight}%
                </span>
                {isCustomWeights && (
                  <span className="text-[11px] font-semibold text-indigo-400 bg-indigo-950/60 px-2 py-0.5 rounded border border-indigo-800">
                    Custom Weights Active
                  </span>
                )}
              </div>
            </div>

            <div className="space-y-4">
              {Object.entries(weights).map(([key, val]) => (
                <div
                  key={key}
                  className="space-y-1.5 p-3 rounded-lg bg-gray-950 border border-gray-800"
                >
                  <div className="flex items-center justify-between text-xs font-semibold">
                    <span className="capitalize text-gray-200">{key} Component</span>
                    <span className="font-mono text-indigo-400">{val}%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="50"
                    step="1"
                    value={val}
                    onChange={(e) =>
                      setWeights((prev) => ({
                        ...prev,
                        [key]: parseInt(e.target.value, 10),
                      }))
                    }
                    className="w-full accent-indigo-500 h-1.5 bg-gray-800 rounded-lg cursor-pointer"
                  />
                  <p className="text-[11px] text-gray-500">
                    {key === "pain" &&
                      "Evaluates missing website, non-HTTPS, low rating, and unanswered complaints."}
                    {key === "fit" &&
                      "Evaluates category match, rating boundary, and region targeting."}
                    {key === "timing" &&
                      "Evaluates recent negative reviews, new businesses, and high-gap hex opportunity."}
                    {key === "reachability" &&
                      "Evaluates named decision-maker email, generic email, and verified phone."}
                    {key === "evidence" &&
                      "Evaluates review volume, complete business hours, and engagement depth."}
                  </p>
                </div>
              ))}
            </div>

            <div className="pt-3 border-t border-gray-800 flex items-center justify-between">
              <button
                onClick={handleResetWeights}
                disabled={saving}
                className="px-3.5 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 font-medium text-xs rounded-lg flex items-center gap-2 transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reset to Defaults</span>
              </button>
              <button
                onClick={handleSaveWeights}
                disabled={saving}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 font-semibold text-xs rounded-lg flex items-center gap-2 transition-colors"
              >
                <Save className="w-4 h-4" />
                <span>{saving ? "Saving..." : "Save Custom Weights"}</span>
              </button>
            </div>
          </div>
        )}

        {/* TAB 3: WORKSPACE CAPS & RETENTION */}
        {activeTab === "caps" && (
          <div className="rounded-xl bg-gray-900 border border-gray-800 p-6 space-y-6">
            <div>
              <h2 className="text-base font-semibold text-white">
                Execution Caps & Data Retention
              </h2>
              <p className="text-xs text-gray-400 mt-0.5">
                Set strict guardrails on map scraping bounds, daily LLM expenses, and automated raw
                data cleanup.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-gray-300">
                  Max H3 Grid Cells per Job
                </label>
                <input
                  type="number"
                  min="1"
                  max="1000"
                  value={caps.max_cells_per_job}
                  onChange={(e) =>
                    setCaps((prev) => ({
                      ...prev,
                      max_cells_per_job: parseInt(e.target.value, 10) || 1,
                    }))
                  }
                  className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-xs text-white focus:ring-1 focus:ring-indigo-500"
                />
                <span className="text-[11px] text-gray-500 block">
                  Default: 250 cells (prevents runaway grid expansion)
                </span>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-gray-300">
                  Max Scraped Places per Job
                </label>
                <input
                  type="number"
                  min="10"
                  max="50000"
                  value={caps.max_places_per_job}
                  onChange={(e) =>
                    setCaps((prev) => ({
                      ...prev,
                      max_places_per_job: parseInt(e.target.value, 10) || 10,
                    }))
                  }
                  className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-xs text-white focus:ring-1 focus:ring-indigo-500"
                />
                <span className="text-[11px] text-gray-500 block">
                  Default: 5,000 places per scraping job
                </span>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-gray-300">
                  Daily LLM Cost Cap ($ USD)
                </label>
                <input
                  type="number"
                  step="0.5"
                  min="0.5"
                  max="100"
                  value={caps.daily_llm_cost_cap_usd}
                  onChange={(e) =>
                    setCaps((prev) => ({
                      ...prev,
                      daily_llm_cost_cap_usd: parseFloat(e.target.value) || 0.5,
                    }))
                  }
                  className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-xs text-white focus:ring-1 focus:ring-indigo-500"
                />
                <span className="text-[11px] text-gray-500 block">
                  Default: $2.00 / day (protects against cost overrun)
                </span>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-gray-300">
                  Raw Scraped Data Retention (Days)
                </label>
                <input
                  type="number"
                  min="7"
                  max="365"
                  value={caps.data_retention_days}
                  onChange={(e) =>
                    setCaps((prev) => ({
                      ...prev,
                      data_retention_days: parseInt(e.target.value, 10) || 30,
                    }))
                  }
                  className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-xs text-white focus:ring-1 focus:ring-indigo-500"
                />
                <span className="text-[11px] text-gray-500 block">
                  Default: 90 days (auto-pruned by Celery beat cleanup)
                </span>
              </div>
            </div>

            <div className="pt-3 border-t border-gray-800 flex justify-end">
              <button
                onClick={handleSaveCaps}
                disabled={saving}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 font-semibold text-xs rounded-lg flex items-center gap-2 transition-colors"
              >
                <Save className="w-4 h-4" />
                <span>{saving ? "Saving..." : "Save Limits & Retention Policy"}</span>
              </button>
            </div>
          </div>
        )}

        {/* TAB 4: API USAGE */}
        {activeTab === "usage" && (
          <div className="space-y-6">
            <div className="rounded-xl bg-gray-900 border border-gray-800 p-6 space-y-4">
              <div>
                <h2 className="text-base font-semibold text-white">
                  Anthropic API & LLM Cost Tracking
                </h2>
                <p className="text-xs text-gray-400 mt-0.5">
                  Real-time token usage and cost accounting for website audits and review theme
                  synthesis.
                </p>
              </div>

              {usage ? (
                <div className="space-y-6 pt-2">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="p-4 rounded-xl bg-gray-950 border border-gray-800">
                      <span className="text-[11px] font-semibold text-gray-400 uppercase">
                        Cost Today
                      </span>
                      <div className="text-2xl font-bold font-mono text-white mt-1">
                        ${usage.cost_today_usd.toFixed(4)}
                      </div>
                      <span className="text-[11px] text-gray-500">
                        Cap: ${usage.daily_cost_cap_usd.toFixed(2)}
                      </span>
                    </div>

                    <div className="p-4 rounded-xl bg-gray-950 border border-gray-800">
                      <span className="text-[11px] font-semibold text-gray-400 uppercase">
                        Remaining Budget
                      </span>
                      <div className="text-2xl font-bold font-mono text-emerald-400 mt-1">
                        ${usage.remaining_budget_today_usd.toFixed(4)}
                      </div>
                      <span className="text-[11px] text-emerald-500">Active today</span>
                    </div>

                    <div className="p-4 rounded-xl bg-gray-950 border border-gray-800">
                      <span className="text-[11px] font-semibold text-gray-400 uppercase">
                        Total Tokens
                      </span>
                      <div className="text-2xl font-bold font-mono text-white mt-1">
                        {((usage.prompt_tokens + usage.completion_tokens) / 1000).toFixed(1)}k
                      </div>
                      <span className="text-[11px] text-gray-500">
                        Prompt: {usage.prompt_tokens}
                      </span>
                    </div>

                    <div className="p-4 rounded-xl bg-gray-950 border border-gray-800">
                      <span className="text-[11px] font-semibold text-gray-400 uppercase">
                        Total Cost (All-Time)
                      </span>
                      <div className="text-2xl font-bold font-mono text-indigo-400 mt-1">
                        ${usage.total_cost_usd.toFixed(4)}
                      </div>
                      <span className="text-[11px] text-gray-500">
                        {usage.total_calls} LLM calls
                      </span>
                    </div>
                  </div>

                  {/* Budget Progress Bar */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-400">Daily Cap Utilization:</span>
                      <span className="font-mono text-white font-semibold">
                        {((usage.cost_today_usd / usage.daily_cost_cap_usd) * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="w-full h-2.5 bg-gray-950 rounded-full overflow-hidden border border-gray-800">
                      <div
                        className="h-full bg-gradient-to-r from-indigo-500 to-emerald-500 rounded-full"
                        style={{
                          width: `${Math.min(100, (usage.cost_today_usd / usage.daily_cost_cap_usd) * 100)}%`,
                        }}
                      />
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-8 text-center text-xs text-gray-500">
                  No LLM calls logged yet.
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 5: ACCOUNT & DATA TOOLS */}
        {activeTab === "account" && (
          <div className="space-y-6">
            {/* User Profile & Security */}
            <div className="rounded-xl bg-gray-900 border border-gray-800 p-6 space-y-4">
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <User className="w-4 h-4 text-indigo-400" />
                <span>Account & Credentials</span>
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div>
                  <span className="text-gray-400">Email Address</span>
                  <p className="font-medium text-white mt-0.5">{user?.email}</p>
                </div>
                <div>
                  <span className="text-gray-400">Workspace Tenant ID</span>
                  <p className="font-mono text-gray-300 mt-0.5">{user?.workspace?.id}</p>
                </div>
                <div>
                  <span className="text-gray-400">Email Verification Status</span>
                  <div className="mt-1 flex items-center gap-2">
                    {user?.is_verified ? (
                      <span className="flex items-center gap-1 text-emerald-400 font-semibold">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Verified</span>
                      </span>
                    ) : (
                      <button
                        onClick={handleRequestVerification}
                        className="px-2.5 py-1 bg-amber-950/80 hover:bg-amber-900 border border-amber-800 text-amber-300 rounded text-[11px] font-medium transition-colors"
                      >
                        Request Verification Link (Stub)
                      </button>
                    )}
                  </div>
                </div>
                <div>
                  <span className="text-gray-400">Password Reset</span>
                  <div className="mt-1">
                    <button
                      onClick={handleForgotPassword}
                      className="px-2.5 py-1 bg-gray-800 hover:bg-gray-700 text-white rounded text-[11px] font-medium transition-colors flex items-center gap-1.5"
                    >
                      <KeyRound className="w-3.5 h-3.5" />
                      <span>Request Password Reset Link</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Data Export (JSON & CSV) */}
            <div className="rounded-xl bg-gray-900 border border-gray-800 p-6 space-y-4">
              <div>
                <h2 className="text-base font-semibold text-white flex items-center gap-2">
                  <Download className="w-4 h-4 text-indigo-400" />
                  <span>Data Export (DPDP / GDPR Compliance)</span>
                </h2>
                <p className="text-xs text-gray-400 mt-0.5">
                  Download all public business records, enriched leads, and outreach events owned by
                  your workspace.
                </p>
              </div>

              <div className="flex flex-wrap gap-3">
                <button
                  onClick={() => handleExport("json")}
                  disabled={isExporting !== null}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-xs font-semibold text-white flex items-center gap-2 transition-colors"
                >
                  <Download className="w-4 h-4" />
                  <span>{isExporting === "json" ? "Exporting..." : "Export as JSON"}</span>
                </button>
                <button
                  onClick={() => handleExport("csv")}
                  disabled={isExporting !== null}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-xs font-semibold text-white flex items-center gap-2 transition-colors"
                >
                  <FileSpreadsheet className="w-4 h-4 text-emerald-400" />
                  <span>{isExporting === "csv" ? "Exporting..." : "Export as CSV"}</span>
                </button>
              </div>
            </div>

            {/* Right to be Forgotten Deletion */}
            <div className="rounded-xl bg-red-950/20 border border-red-900/50 p-6 space-y-4">
              <div>
                <h2 className="text-base font-semibold text-red-300 flex items-center gap-2">
                  <Trash2 className="w-4 h-4 text-red-400" />
                  <span>Irreversible Workspace Deletion (Right to be Forgotten)</span>
                </h2>
                <p className="text-xs text-red-200/70 mt-0.5">
                  Permanently erase all places, leads, ML snapshots, and search jobs. This action
                  cannot be undone.
                </p>
              </div>

              <div className="space-y-3 max-w-md">
                <label className="text-xs text-red-200/80 block">
                  To confirm, type <strong className="text-white font-mono">DELETE MY DATA</strong>{" "}
                  below:
                </label>
                <input
                  type="text"
                  value={confirmDeleteText}
                  onChange={(e) => setConfirmDeleteText(e.target.value)}
                  placeholder="DELETE MY DATA"
                  className="w-full bg-gray-950 border border-red-900/60 rounded-lg p-2.5 text-xs text-white placeholder-gray-600 focus:ring-1 focus:ring-red-500"
                />
                <button
                  onClick={handleDeleteData}
                  disabled={confirmDeleteText !== "DELETE MY DATA" || isDeleting}
                  className="px-4 py-2 bg-red-600 hover:bg-red-500 disabled:opacity-40 disabled:hover:bg-red-600 text-white font-semibold text-xs rounded-lg transition-colors"
                >
                  {isDeleting ? "Deleting..." : "Permanently Delete All Workspace Data"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
