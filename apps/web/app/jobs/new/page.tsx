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
    <div className="min-h-screen bg-gray-950 text-white p-6 sm:p-10">
      <div className="max-w-4xl mx-auto space-y-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Compass className="w-7 h-7 text-indigo-400" />
            New Market Gap Analysis
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Specify a target business category and geographic area to scan and score.
          </p>
        </div>

        {submitError && (
          <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span>{submitError}</span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Form */}
          <div className="lg:col-span-2 bg-gray-900 border border-gray-800 rounded-2xl p-6 sm:p-8 space-y-6">
            <form onSubmit={handleSubmit} data-testid="new-job-form" className="space-y-6">
              <div>
                <label htmlFor="category" className="block text-sm font-medium text-gray-300 mb-2">
                  Target Category
                </label>
                <select
                  id="category"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-gray-950 border border-gray-800 text-white text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                >
                  {CATEGORIES.map((cat) => (
                    <option key={cat.value} value={cat.value}>
                      {cat.label}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1.5">
                  Controlled taxonomy used for cleaning and benchmark calculations.
                </p>
              </div>

              <div>
                <label htmlFor="areaName" className="block text-sm font-medium text-gray-300 mb-2">
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
                    className="w-full px-4 py-2.5 pl-10 rounded-xl bg-gray-950 border border-gray-800 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                  <MapPin className="w-4 h-4 text-gray-500 absolute left-3.5 top-3" />
                </div>
                <p className="text-xs text-gray-500 mt-1.5">
                  Geocoded via OpenStreetMap Nominatim with cached bounding boxes.
                </p>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label
                    htmlFor="cellSize"
                    className="text-sm font-medium text-gray-300 flex items-center gap-1.5"
                  >
                    <Sliders className="w-4 h-4 text-gray-400" />
                    Search Cell Size: {cellSizeM}m
                  </label>
                  <span className="text-xs text-gray-500">
                    {cellSizeM <= 1000 ? "High resolution (dense)" : "Broader sweep"}
                  </span>
                </div>
                <input
                  id="cellSize"
                  type="range"
                  min="500"
                  max="3000"
                  step="250"
                  value={cellSizeM}
                  onChange={(e) => setCellSizeM(Number(e.target.value))}
                  className="w-full accent-indigo-500 cursor-pointer"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
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
                    <p className="text-amber-200/80 leading-relaxed">
                      Automated scraping of Google Maps may violate Google&apos;s Terms of Service.
                      GapScout is designed strictly for processing public business information for
                      legitimate market intelligence and lawful B2B outreach in compliance with
                      applicable data protection laws (e.g. DPDP Act / GDPR).
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
                    className="mt-0.5 rounded border-amber-400/40 text-indigo-600 focus:ring-indigo-500 bg-gray-950"
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
                className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-colors disabled:opacity-50 mt-4 shadow-lg shadow-indigo-600/20"
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

          {/* Dry Run Preview / Summary */}
          <div className="space-y-6">
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 space-y-4">
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <Layers className="w-5 h-5 text-indigo-400" />
                <span>Dry-Run Estimate</span>
              </h2>

              {isEstimating ? (
                <div className="py-12 flex flex-col items-center justify-center text-gray-400 text-sm gap-2">
                  <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
                  <span>Calculating grid & runtime...</span>
                </div>
              ) : estimateError ? (
                <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs">
                  {estimateError}
                </div>
              ) : estimate ? (
                <div className="space-y-4 pt-2">
                  <div className="flex items-center justify-between pb-3 border-b border-gray-800 text-sm">
                    <span className="text-gray-400 flex items-center gap-1.5">
                      <Layers className="w-4 h-4 text-gray-500" />
                      Search Cells
                    </span>
                    <span className="font-mono font-semibold text-white">
                      {estimate.cells_total} cells
                    </span>
                  </div>

                  <div className="flex items-center justify-between pb-3 border-b border-gray-800 text-sm">
                    <span className="text-gray-400 flex items-center gap-1.5">
                      <MapPin className="w-4 h-4 text-gray-500" />
                      Coverage Area
                    </span>
                    <span className="font-mono font-semibold text-white">
                      {estimate.area_km2.toFixed(1)} km²
                    </span>
                  </div>

                  <div className="flex items-center justify-between pb-3 border-b border-gray-800 text-sm">
                    <span className="text-gray-400 flex items-center gap-1.5">
                      <Clock className="w-4 h-4 text-gray-500" />
                      Estimated Runtime
                    </span>
                    <span className="font-mono font-semibold text-white">
                      ~{Math.round(estimate.estimated_runtime_sec)}s
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-400 flex items-center gap-1.5">
                      <DollarSign className="w-4 h-4 text-gray-500" />
                      Estimated Cost
                    </span>
                    <span className="font-mono font-semibold text-emerald-400">
                      ${estimate.estimated_cost_usd.toFixed(2)}
                    </span>
                  </div>

                  {estimate.bbox && (
                    <div className="pt-2 text-[11px] text-gray-500 font-mono bg-gray-950 p-3 rounded-lg border border-gray-800">
                      BBox: [{estimate.bbox.min_lat.toFixed(4)}, {estimate.bbox.min_lon.toFixed(4)}]
                      to [{estimate.bbox.max_lat.toFixed(4)}, {estimate.bbox.max_lon.toFixed(4)}]
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-xs text-gray-500 py-6 text-center">
                  Enter an area name above to preview the coverage grid and estimates.
                </p>
              )}
            </div>

            <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800 text-xs text-gray-400 space-y-2">
              <div className="flex items-center gap-1.5 text-gray-300 font-medium">
                <HelpCircle className="w-4 h-4 text-indigo-400" />
                <span>Automatic Pipeline</span>
              </div>
              <p>
                When a search job completes, GapScout automatically runs normalisation,
                deduplication, phone/website cleaning, and H3 resolution 8 gap analysis.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
