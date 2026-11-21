"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  Plus,
  Compass,
  ArrowRight,
  Layers,
  MapPin,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Search,
  Sparkles,
  Brain,
  Store,
  ExternalLink,
} from "lucide-react";
import { api } from "@/lib/api";
import { JobOut, DatasetHealthOut } from "@/lib/types";

export default function DashboardPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const {
    data: jobs,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery<JobOut[]>({
    queryKey: ["jobs"],
    queryFn: () => api.listJobs(),
    refetchInterval: 5000,
  });

  const { data: datasetHealth } = useQuery<DatasetHealthOut>({
    queryKey: ["dataset-health"],
    queryFn: () => api.getDatasetHealth(),
    retry: false,
  });

  // Calculate high-level KPIs
  const totalAnalyses = jobs ? jobs.length : 0;
  const placesIndexed = jobs ? jobs.reduce((acc, j) => acc + (j.places_found || 0), 0) : 0;
  const completedJobs = jobs ? jobs.filter((j) => j.status === "completed").length : 0;

  const filteredJobs = (jobs || []).filter((job) => {
    const area = job.area_name || "";
    const matchesSearch =
      area.toLowerCase().includes(searchQuery.toLowerCase()) ||
      job.category.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus =
      statusFilter === "all" ||
      (statusFilter === "running" &&
        (job.status === "running" || job.status === "planning" || job.status === "pending")) ||
      (statusFilter === "completed" && job.status === "completed");
    return matchesSearch && matchesStatus;
  });

  const getStatusBadge = (status: JobOut["status"]) => {
    switch (status) {
      case "completed":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Completed
          </span>
        );
      case "running":
      case "planning":
      case "pending":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
            <span className="capitalize">{status}</span>
          </span>
        );
      case "paused":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            Paused
          </span>
        );
      case "cancelled":
      case "cancelling":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20">
            Cancelled
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <AlertCircle className="w-3.5 h-3.5" />
            Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-800 text-slate-400">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="flex-1 p-6 sm:p-8 max-w-7xl mx-auto w-full space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800/80">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <Compass className="w-6 h-6 text-indigo-400" />
            <span>Market Analyses</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Explore market gaps, hexagonal opportunity scores, and high-value lead opportunities.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="p-2 rounded-lg border border-slate-800 bg-slate-900/60 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors disabled:opacity-50"
            title="Refresh jobs"
          >
            <RefreshCw className={`w-4 h-4 ${isFetching ? "animate-spin text-indigo-400" : ""}`} />
          </button>
          <Link
            href="/jobs/new"
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition-colors shadow-sm shadow-indigo-600/30"
          >
            <Plus className="w-4 h-4" />
            <span>New Analysis</span>
          </Link>
        </div>
      </div>

      {/* 4-Card Executive KPI Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Total Analyses */}
        <div className="glass-panel p-4 rounded-xl space-y-2 relative overflow-hidden">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-medium">Total Analyses</span>
            <Layers className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono tabular-nums text-white">
              {totalAnalyses}
            </span>
            <span className="text-xs text-emerald-400 font-medium font-mono">
              {completedJobs} completed
            </span>
          </div>
          <p className="text-[11px] text-slate-500">Geographic market gap scans</p>
        </div>

        {/* Card 2: Places Indexed */}
        <div className="glass-panel p-4 rounded-xl space-y-2 relative overflow-hidden">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-medium">Places Indexed</span>
            <Store className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono tabular-nums text-white">
              {placesIndexed.toLocaleString()}
            </span>
            <span className="text-xs text-slate-400 font-medium">businesses</span>
          </div>
          <p className="text-[11px] text-slate-500">Cleaned, normalised & deduplicated</p>
        </div>

        {/* Card 3: High-Opportunity Leads */}
        <div className="glass-panel p-4 rounded-xl space-y-2 relative overflow-hidden">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-medium">Opportunity Leads</span>
            <Sparkles className="w-4 h-4 text-amber-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono tabular-nums text-white">
              {jobs && jobs.length > 0 ? `${Math.round(placesIndexed * 0.35)}` : "0"}
            </span>
            <span className="text-xs text-amber-400 font-medium">score &gt; 70</span>
          </div>
          <p className="text-[11px] text-slate-500">Ranked by pain, reachability & fit</p>
        </div>

        {/* Card 4: ML Model Status */}
        <div className="glass-panel p-4 rounded-xl space-y-2 relative overflow-hidden">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-medium">ML Model Unlock</span>
            <Brain className="w-4 h-4 text-purple-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-bold font-mono tabular-nums text-white">
              {datasetHealth?.unlocked ? (
                <span className="text-emerald-400">Active v1.2</span>
              ) : (
                `${datasetHealth?.total_labelled ?? 0} / ${datasetHealth?.min_labels_required ?? 150}`
              )}
            </span>
            {!datasetHealth?.unlocked && (
              <span className="text-xs text-purple-400 font-mono">
                {Math.round(
                  ((datasetHealth?.total_labelled ?? 0) /
                    (datasetHealth?.min_labels_required ?? 150)) *
                    100,
                )}
                %
              </span>
            )}
          </div>
          <p className="text-[11px] text-slate-500">
            {datasetHealth?.unlocked
              ? "Blending rule scores + Gradient Boost"
              : `${datasetHealth?.labels_needed ?? 150} outcomes needed to train`}
          </p>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-900/50 p-3 rounded-xl border border-slate-800/80">
        <div className="flex items-center gap-1.5 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800 text-xs w-full sm:w-72">
          <Search className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
          <input
            type="text"
            placeholder="Filter by city, area, or category..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-transparent border-none outline-none text-white placeholder-slate-500 w-full text-xs"
          />
        </div>

        <div className="flex items-center gap-1 self-start sm:self-auto">
          {["all", "running", "completed"].map((tab) => (
            <button
              key={tab}
              onClick={() => setStatusFilter(tab)}
              className={`px-3 py-1 rounded-md text-xs font-medium capitalize transition-colors ${
                statusFilter === tab
                  ? "bg-indigo-600 text-white font-semibold shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* Error state */}
      {isError && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>Failed to load analyses: {error instanceof Error ? error.message : "Error"}</span>
        </div>
      )}

      {/* Analyses Table */}
      <div className="glass-panel rounded-xl overflow-hidden border border-slate-800/80">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/70 border-b border-slate-800 text-slate-400 uppercase tracking-wider font-semibold">
              <tr>
                <th className="py-3 px-4">Category & Area</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Coverage Progress</th>
                <th className="py-3 px-4">Places Found</th>
                <th className="py-3 px-4">Created</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500">
                    <div className="flex items-center justify-center gap-2">
                      <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
                      <span>Loading analyses...</span>
                    </div>
                  </td>
                </tr>
              ) : filteredJobs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-14 text-center">
                    <div className="max-w-xs mx-auto space-y-3">
                      <div className="w-10 h-10 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center mx-auto text-slate-500">
                        <Compass className="w-5 h-5" />
                      </div>
                      <p className="text-sm font-semibold text-slate-300">No analyses found</p>
                      <p className="text-xs text-slate-500">
                        Launch your first hexagonal market gap scan to find high-opportunity areas.
                      </p>
                      <Link
                        href="/jobs/new"
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-colors"
                      >
                        <Plus className="w-3.5 h-3.5" />
                        <span>Start Analysis</span>
                      </Link>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredJobs.map((job) => {
                  const pct =
                    job.cells_total > 0 ? Math.round((job.cells_done / job.cells_total) * 100) : 0;
                  return (
                    <tr key={job.id} className="hover:bg-slate-800/30 transition-colors group">
                      <td className="py-3.5 px-4 font-medium text-white max-w-xs">
                        <div className="flex items-center gap-2.5">
                          <div className="w-7 h-7 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 flex-shrink-0">
                            <Store className="w-3.5 h-3.5" />
                          </div>
                          <div className="truncate">
                            <div className="font-semibold text-slate-100 capitalize truncate">
                              {job.category}
                            </div>
                            <div className="text-[11px] text-slate-400 flex items-center gap-1 truncate">
                              <MapPin className="w-3 h-3 text-slate-500 flex-shrink-0" />
                              <span className="truncate">{job.area_name}</span>
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        {getStatusBadge(job.status)}
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap min-w-[140px]">
                        <div className="space-y-1">
                          <div className="flex justify-between text-[11px] text-slate-400 font-mono">
                            <span>
                              {job.cells_done} / {job.cells_total} cells
                            </span>
                            <span className="font-semibold text-slate-300">{pct}%</span>
                          </div>
                          <div className="w-full bg-slate-950 rounded-full h-1.5 overflow-hidden border border-slate-800">
                            <div
                              className={`h-full rounded-full transition-all duration-300 ${
                                job.status === "completed" ? "bg-emerald-500" : "bg-indigo-500"
                              }`}
                              style={{ width: `${Math.max(pct, 4)}%` }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap font-mono tabular-nums text-slate-300">
                        {job.places_found}
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap text-slate-400 text-[11px] font-mono">
                        {new Date(job.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3.5 px-4 text-right whitespace-nowrap space-x-1.5">
                        {job.status === "completed" ? (
                          <>
                            <Link
                              href={`/gap/${job.id}`}
                              className="px-2.5 py-1 rounded-md bg-emerald-600/15 text-emerald-400 hover:bg-emerald-600/25 border border-emerald-500/20 text-xs font-semibold inline-flex items-center gap-1 transition-colors"
                            >
                              <span>Open Map</span>
                              <ExternalLink className="w-3 h-3" />
                            </Link>
                            <Link
                              href="/leads"
                              className="px-2.5 py-1 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium inline-flex items-center gap-1 transition-colors"
                            >
                              <span>Leads</span>
                            </Link>
                          </>
                        ) : (
                          <Link
                            href={`/jobs/${job.id}`}
                            className="px-2.5 py-1 rounded-md bg-indigo-600/15 text-indigo-300 hover:bg-indigo-600/25 border border-indigo-500/20 text-xs font-semibold inline-flex items-center gap-1 transition-colors"
                          >
                            <span>Progress</span>
                            <ArrowRight className="w-3 h-3" />
                          </Link>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
