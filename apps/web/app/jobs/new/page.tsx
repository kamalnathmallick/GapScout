"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Compass,
  ArrowRight,
  Loader2,
  Sliders,
  DollarSign,
  Clock,
  Layers,
  MapPin,
  AlertCircle,
  HelpCircle,
  Grid,
} from "lucide-react";
import { api } from "@/lib/api";
import { GridEstimateOut } from "@/lib/types";

const CATEGORIES = [
  { value: "cafe", label: "Cafe & Coffee Shop" },
  { value: "restaurant", label: "Restaurant" },
  { value: "gym", label: "Gym & Fitness Studio" },
  { value: "salon", label: "Hair & Beauty Salon" },
  { value: "dental clinic", label: "Dental Clinic" },
  { value: "coaching centre", label: "Coaching Centre / Tutoring" },
];

export default function NewJobPage() {
  const router = useRouter();
  const [category, setCategory] = useState("cafe");
  const [areaName, setAreaName] = useState("Indiranagar, Bangalore");
  const [cellSizeM, setCellSizeM] = useState(1000);
  const [acknowledgedTos, setAcknowledgedTos] = useState(false);

  const [estimate, setEstimate] = useState<GridEstimateOut | null>(null);
  const [isEstimating, setIsEstimating] = useState(false);
  const [estimateError, setEstimateError] = useState<string | null>(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Debounced estimation call
  useEffect(() => {
    const timer = setTimeout(async () => {
      if (!areaName.trim()) {
        setEstimate(null);
        return;
      }

      setIsEstimating(true);
      setEstimateError(null);
      try {
        const est = await api.estimateGrid({
          category,
          area_name: areaName.trim(),
          cell_size_m: cellSizeM,
        });
        setEstimate(est);
      } catch (err: unknown) {
        setEstimateError(
          err instanceof Error ? err.message : "Could not estimate grid for this area.",
        );
        setEstimate(null);
      } finally {
        setIsEstimating(false);
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [category, areaName, cellSizeM]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!areaName.trim()) return;

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const job = await api.createJob({
        category,
        area_name: areaName.trim(),
        cell_size_m: cellSizeM,
      });
      router.push(`/jobs/${job.id}`);
    } catch (err: unknown) {
      setSubmitError(err instanceof Error ? err.message : "Failed to create search job");
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex-1 p-6 sm:p-8 max-w-6xl mx-auto w-full space-y-8">
      {/* Header */}
      <div className="pb-6 border-b border-slate-800/80">
        <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
          <Compass className="w-6 h-6 text-indigo-400" />
          <span>New Market Gap Analysis</span>
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Specify a target business category and geographic area to scan, normalize, and score on an
          H3 hexagonal grid.
        </p>
      </div>

      {submitError && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{submitError}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Form Column (Left 2 cols) */}
        <div className="lg:col-span-2 glass-panel rounded-2xl p-6 sm:p-8 space-y-6 border border-slate-800/80">
          <form onSubmit={handleSubmit} data-testid="new-job-form" className="space-y-6">
            <div>
              <label
                htmlFor="category"
                className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2"
              >
                Target Category
              </label>
              <select
                id="category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950/80 border border-slate-800 text-white text-xs sm:text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
              >
                {CATEGORIES.map((cat) => (
                  <option key={cat.value} value={cat.value} className="bg-slate-900 text-white">
                    {cat.label}
                  </option>
                ))}
              </select>
              <p className="text-[11px] text-slate-500 mt-1.5">
                Standardised taxonomy for supply aggregation and benchmark metrics.
              </p>
            </div>

            <div>
              <label
                htmlFor="areaName"
                className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2"
              >
                City or Neighbourhood Name
              </label>
              <div className="relative">
                <input
                  id="areaName"
                  type="text"
                  required
                  value={areaName}
                  onChange={(e) => setAreaName(e.target.value)}
                  placeholder="e.g. Koramangala, Bangalore or Downtown Austin"
                  className="w-full px-3.5 py-2.5 pl-10 rounded-xl bg-slate-950/80 border border-slate-800 text-white placeholder-slate-500 text-xs sm:text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
                />
                <MapPin className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
              </div>
              <p className="text-[11px] text-slate-500 mt-1.5">
                Geocoded via OpenStreetMap Nominatim with cached bounding boxes.
              </p>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label
                  htmlFor="cellSize"
                  className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5"
                >
                  <Sliders className="w-3.5 h-3.5 text-slate-400" />
                  <span>Search Cell Size: {cellSizeM}m</span>
                </label>
                <span className="text-[11px] font-mono text-slate-400">
                  {cellSizeM <= 1000 ? "Dense urban (high res)" : "Broader sweep"}
                </span>
              </div>
              <input
                id="cellSize"
                type="range"
                role="slider"
                aria-label="Search Cell Size"
                min="500"
                max="3000"
                step="250"
                value={cellSizeM}
                onChange={(e) => setCellSizeM(Number(e.target.value))}
                className="w-full accent-indigo-500 cursor-pointer"
              />
              <div className="flex justify-between text-[11px] text-slate-500 mt-1 font-mono">
                <span>500m (Dense urban)</span>
                <span>1500m</span>
                <span>3000m (Suburban)</span>
              </div>
            </div>

            {/* Compliance & Scraping Notice */}
            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-200/90 space-y-3">
              <div className="flex items-start gap-2.5">
                <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <h3 className="font-semibold text-amber-300">
                    Scraping Notice &amp; Legal Compliance
                  </h3>
                  <p className="text-amber-200/80 leading-relaxed text-[11px]">
                    Automated scraping of Google Maps may violate Google&apos;s Terms of Service.
                    GapScout is designed strictly for processing public business information for
                    legitimate market intelligence and lawful B2B outreach in compliance with
                    applicable data protection regulations.
                  </p>
                </div>
              </div>
              <label className="flex items-start gap-2.5 cursor-pointer pt-2 border-t border-amber-500/20">
                <input
                  type="checkbox"
                  id="acknowledgedTos"
                  data-testid="tos-checkbox"
                  checked={acknowledgedTos}
                  onChange={(e) => setAcknowledgedTos(e.target.checked)}
                  className="mt-0.5 rounded border-amber-400/40 text-indigo-600 focus:ring-indigo-500 bg-slate-950"
                />
                <span className="text-xs text-amber-100 select-none">
                  I acknowledge the Google Terms of Service risks and confirm this search job
                  complies with data privacy regulations.
                </span>
              </label>
            </div>

            <button
              type="submit"
              disabled={isSubmitting || isEstimating || !estimate || !acknowledgedTos}
              className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs sm:text-sm transition-all disabled:opacity-50 mt-4 shadow-lg shadow-indigo-600/20 hover:scale-[1.01]"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Launching analysis...</span>
                </>
              ) : (
                <>
                  <span>Confirm and Start Analysis</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        </div>

        {/* Sticky Dry Run Preview / Summary Column (Right 1 col) */}
        <div className="space-y-6">
          <div className="glass-panel rounded-2xl p-6 space-y-4 border border-slate-800/80 sticky top-20">
            <h2 className="text-sm font-semibold text-white flex items-center gap-2">
              <Layers className="w-4 h-4 text-indigo-400" />
              <span>Dry-Run Estimate</span>
            </h2>

            {isEstimating ? (
              <div className="py-12 flex flex-col items-center justify-center text-slate-400 text-xs gap-2">
                <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
                <span>Calculating grid & runtime...</span>
              </div>
            ) : estimateError ? (
              <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs">
                {estimateError}
              </div>
            ) : estimate ? (
              <div className="space-y-3.5 pt-1">
                {/* Visual Mini Grid */}
                <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800/80 flex items-center justify-center">
                  <div className="grid grid-cols-3 gap-1 w-24 h-24">
                    {Array.from({ length: Math.min(estimate.cells_total, 9) }).map((_, i) => (
                      <div
                        key={i}
                        className="rounded bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-[10px] text-indigo-300 font-mono"
                      >
                        {i + 1}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex items-center justify-between pb-2.5 border-b border-slate-800 text-xs">
                  <span className="text-slate-400 flex items-center gap-1.5">
                    <Grid className="w-3.5 h-3.5 text-slate-500" />
                    <span>Search Cells</span>
                  </span>
                  <span className="font-mono font-bold text-white tabular-nums">
                    {estimate.cells_total} cells
                  </span>
                </div>

                <div className="flex items-center justify-between pb-2.5 border-b border-slate-800 text-xs">
                  <span className="text-slate-400 flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5 text-slate-500" />
                    <span>Coverage Area</span>
                  </span>
                  <span className="font-mono font-bold text-white tabular-nums">
                    {estimate.area_km2.toFixed(1)} km²
                  </span>
                </div>

                <div className="flex items-center justify-between pb-2.5 border-b border-slate-800 text-xs">
                  <span className="text-slate-400 flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-slate-500" />
                    <span>Estimated Runtime</span>
                  </span>
                  <span className="font-mono font-bold text-white tabular-nums">
                    ~{Math.round(estimate.estimated_runtime_sec)}s
                  </span>
                </div>

                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400 flex items-center gap-1.5">
                    <DollarSign className="w-3.5 h-3.5 text-slate-500" />
                    <span>Estimated Cost</span>
                  </span>
                  <span className="font-mono font-bold text-emerald-400 tabular-nums">
                    ${estimate.estimated_cost_usd.toFixed(2)}
                  </span>
                </div>

                {estimate.bbox && (
                  <div className="pt-2 text-[10px] text-slate-500 font-mono bg-slate-950 p-2.5 rounded-lg border border-slate-800/80 leading-relaxed">
                    BBox: [{estimate.bbox.min_lat.toFixed(4)}, {estimate.bbox.min_lon.toFixed(4)}]
                    to [{estimate.bbox.max_lat.toFixed(4)}, {estimate.bbox.max_lon.toFixed(4)}]
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-slate-500 py-6 text-center">
                Enter an area name above to preview the coverage grid and estimates.
              </p>
            )}

            <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/60 text-xs text-slate-400 space-y-1.5">
              <div className="flex items-center gap-1.5 text-slate-200 font-medium text-[11px]">
                <HelpCircle className="w-3.5 h-3.5 text-indigo-400" />
                <span>Automatic Post-Processing</span>
              </div>
              <p className="text-[11px] leading-relaxed text-slate-500">
                GapScout cleans, dedupes, resolves website domain health, and indexes every place
                into H3 resolution 8 cells automatically upon completion.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
