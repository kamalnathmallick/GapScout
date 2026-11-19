"use client";

import React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  Plus,
  Compass,
  ArrowRight,
  Clock,
  Layers,
  MapPin,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";
import { api } from "@/lib/api";
import { JobOut } from "@/lib/types";

export default function DashboardPage() {
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

  const getStatusBadge = (status: JobOut["status"]) => {
    switch (status) {
      case "completed":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Completed
          </span>
        );
      case "running":
      case "planning":
      case "pending":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20 animate-pulse">
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            {status}
          </span>
        );
      case "paused":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
            Paused
          </span>
        );
      case "cancelled":
      case "cancelling":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-gray-500/10 text-gray-400 border border-gray-500/20">
            Cancelled
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/20">
            <AlertCircle className="w-3.5 h-3.5" />
            Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-gray-800 text-gray-400">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6 sm:p-10">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-gray-800">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <Compass className="w-7 h-7 text-indigo-400" />
              Market Analyses
            </h1>
            <p className="text-sm text-gray-400 mt-1">
              Explore market gaps, hexagonal opportunity scores, and high-value lead opportunities.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="p-2.5 rounded-xl border border-gray-800 bg-gray-900 text-gray-400 hover:text-white transition-colors disabled:opacity-50"
              title="Refresh jobs"
            >
              <RefreshCw className={`w-4 h-4 ${isFetching ? "animate-spin" : ""}`} />
            </button>
            <Link
              href="/jobs/new"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-colors shadow-lg shadow-indigo-600/20"
            >
              <Plus className="w-4 h-4" />
              <span>New Analysis</span>
            </Link>
          </div>
        </div>

        {/* Content State */}
        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-24 rounded-2xl bg-gray-900 border border-gray-800 animate-pulse p-6"
              />
            ))}
          </div>
        ) : isError ? (
          <div className="p-6 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            Failed to load jobs: {error instanceof Error ? error.message : "Unknown error"}
          </div>
        ) : !jobs || jobs.length === 0 ? (
          <div className="text-center py-20 px-6 rounded-3xl bg-gray-900/50 border border-gray-800">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-indigo-500/10 text-indigo-400 mb-4">
              <Compass className="w-8 h-8" />
            </div>
            <h2 className="text-xl font-bold text-white mb-2">No analyses yet</h2>
            <p className="text-sm text-gray-400 max-w-md mx-auto mb-6">
              Start by selecting a city area and business category. GapScout will scan search cells,
              deduplicate listings, and compute hexagonal opportunity scores.
            </p>
            <Link
              href="/jobs/new"
              className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>Run your first analysis</span>
            </Link>
          </div>
        ) : (
          <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden shadow-xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="border-b border-gray-800 bg-gray-950/60 text-gray-400 text-xs font-semibold uppercase tracking-wider">
                    <th className="py-4 px-6">Category & Area</th>
                    <th className="py-4 px-6">Status</th>
                    <th className="py-4 px-6">Progress</th>
                    <th className="py-4 px-6">Places Found</th>
                    <th className="py-4 px-6">Created</th>
                    <th className="py-4 px-6 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {jobs.map((job) => {
                    const isDone = job.status === "completed";
                    const pct =
                      job.cells_total > 0
                        ? Math.round((job.cells_done / job.cells_total) * 100)
                        : 0;

                    return (
                      <tr key={job.id} className="hover:bg-gray-800/40 transition-colors group">
                        <td className="py-4 px-6">
                          <div className="font-semibold text-white capitalize flex items-center gap-2">
                            <span>{job.category}</span>
                          </div>
                          <div className="text-xs text-gray-400 flex items-center gap-1.5 mt-1">
                            <MapPin className="w-3.5 h-3.5 text-gray-500" />
                            <span>{job.area_name || "Custom Region"}</span>
                          </div>
                        </td>
                        <td className="py-4 px-6">{getStatusBadge(job.status)}</td>
                        <td className="py-4 px-6">
                          <div className="flex items-center gap-3">
                            <div className="w-28 bg-gray-800 rounded-full h-2 overflow-hidden">
                              <div
                                className={`h-2 rounded-full transition-all duration-500 ${
                                  isDone ? "bg-emerald-500" : "bg-indigo-500"
                                }`}
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                            <span className="text-xs text-gray-400 font-mono">
                              {job.cells_done}/{job.cells_total} ({pct}%)
                            </span>
                          </div>
                        </td>
                        <td className="py-4 px-6">
                          <span className="inline-flex items-center gap-1.5 text-xs text-gray-300 font-mono">
                            <Layers className="w-3.5 h-3.5 text-gray-500" />
                            {job.places_found} places
                          </span>
                        </td>
                        <td className="py-4 px-6 text-xs text-gray-400">
                          <span className="inline-flex items-center gap-1.5">
                            <Clock className="w-3.5 h-3.5 text-gray-500" />
                            {new Date(job.created_at).toLocaleDateString(undefined, {
                              month: "short",
                              day: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                        </td>
                        <td className="py-4 px-6 text-right">
                          <div className="flex items-center justify-end gap-2">
                            {isDone ? (
                              <Link
                                href={`/gap/${job.id}`}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 text-xs font-medium border border-emerald-500/30 transition-colors"
                              >
                                <span>Gap Map</span>
                                <ArrowRight className="w-3.5 h-3.5" />
                              </Link>
                            ) : null}
                            <Link
                              href={`/jobs/${job.id}`}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-medium transition-colors"
                            >
                              <span>Details</span>
                              <ArrowRight className="w-3.5 h-3.5" />
                            </Link>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
