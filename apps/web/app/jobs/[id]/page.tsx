"use client";

import React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  StopCircle,
  PlayCircle,
  Globe,
  Phone,
  Mail,
  ShieldCheck,
  TrendingUp,
} from "lucide-react";
import { api } from "@/lib/api";
import { JobProgressOut } from "@/lib/types";

export default function JobDetailPage() {
  const params = useParams();
  const jobId = (params?.id as string) || "";
  const queryClient = useQueryClient();

  const {
    data: job,
    isLoading,
    isError,
    error,
  } = useQuery<JobProgressOut>({
    queryKey: ["job", jobId],
    queryFn: () => api.getJob(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "completed" || status === "failed" || status === "cancelled") {
        return false;
      }
      return 3000;
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => api.cancelJob(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["job", jobId] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });

  const resumeMutation = useMutation({
    mutationFn: () => api.resumeJob(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["job", jobId] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-950 text-white p-6 sm:p-10 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="w-8 h-8 animate-spin text-indigo-400" />
          <p className="text-sm text-gray-400">Loading analysis status...</p>
        </div>
      </div>
    );
  }

  if (isError || !job) {
    return (
      <div className="min-h-screen bg-gray-950 text-white p-6 sm:p-10">
        <div className="max-w-3xl mx-auto p-6 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          Failed to load job details: {error instanceof Error ? error.message : "Not found"}
        </div>
      </div>
    );
  }

  const isCompleted = job.status === "completed";
  const isRunning =
    job.status === "running" || job.status === "pending" || job.status === "planning";
  const isCanResume = job.status === "paused" || job.status === "cancelled";

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6 sm:p-10">
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Header & Controls */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-gray-800">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-gray-500 mb-1">
              <span>JOB ID</span>
              <span className="text-gray-300">{job.job_id}</span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
              <span>Analysis Progress</span>
              {isCompleted ? (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Completed
                </span>
              ) : isRunning ? (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20 animate-pulse">
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  {job.status}
                </span>
              ) : (
                <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-gray-800 text-gray-400">
                  {job.status}
                </span>
              )}
            </h1>
          </div>

          <div className="flex items-center gap-3">
            {isRunning && (
              <button
                onClick={() => cancelMutation.mutate()}
                disabled={cancelMutation.isPending}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-gray-900 border border-gray-800 hover:border-red-500/30 text-gray-300 hover:text-red-400 text-sm font-medium transition-colors"
              >
                <StopCircle className="w-4 h-4" />
                <span>Cancel</span>
              </button>
            )}

            {isCanResume && (
              <button
                onClick={() => resumeMutation.mutate()}
                disabled={resumeMutation.isPending}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors"
              >
                <PlayCircle className="w-4 h-4" />
                <span>Resume</span>
              </button>
            )}

            {isCompleted && (
              <Link
                href={`/gap/${job.job_id}`}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium transition-colors shadow-lg shadow-emerald-600/20"
              >
                <span>View Interactive Gap Map</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            )}
          </div>
        </div>

        {/* Live Progress Bar Card */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 sm:p-8 space-y-6">
          <div>
            <div className="flex justify-between items-center text-sm mb-2">
              <span className="text-gray-400 font-medium flex items-center gap-2">
                <span>Coverage Grid Execution</span>
                {isRunning && (
                  <span className="text-xs text-indigo-400 font-mono">(Polling every 3s)</span>
                )}
              </span>
              <span className="font-mono text-white font-bold">{job.pct_complete}%</span>
            </div>
            <div className="w-full bg-gray-950 rounded-full h-3.5 overflow-hidden border border-gray-800 p-0.5">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  isCompleted ? "bg-emerald-500" : "bg-indigo-500"
                }`}
                style={{ width: `${Math.max(job.pct_complete, 2)}%` }}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-2">
            <div className="bg-gray-950 border border-gray-800 rounded-xl p-4">
              <span className="text-xs text-gray-500 block mb-1">Cells Done / Total</span>
              <span className="text-xl font-bold font-mono text-white">
                {job.cells_done} / {job.cells_total}
              </span>
            </div>

            <div className="bg-gray-950 border border-gray-800 rounded-xl p-4">
              <span className="text-xs text-gray-500 block mb-1">Places Found</span>
              <span className="text-xl font-bold font-mono text-indigo-400">
                {job.places_found}
              </span>
            </div>

            <div className="bg-gray-950 border border-gray-800 rounded-xl p-4">
              <span className="text-xs text-gray-500 block mb-1">Errors</span>
              <span
                className={`text-xl font-bold font-mono ${
                  job.errors_count > 0 ? "text-red-400" : "text-gray-400"
                }`}
              >
                {job.errors_count}
              </span>
            </div>

            <div className="bg-gray-950 border border-gray-800 rounded-xl p-4">
              <span className="text-xs text-gray-500 block mb-1">Status</span>
              <span className="text-base font-semibold capitalize text-gray-200">{job.status}</span>
            </div>
          </div>
        </div>

        {/* Quality Report (when available) */}
        {job.quality_report && (
          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 sm:p-8 space-y-6">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-6 h-6 text-emerald-400" />
              <h2 className="text-lg font-bold text-white">Data Quality Report</h2>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="bg-gray-950 p-4 rounded-xl border border-gray-800">
                <span className="text-xs text-gray-500 block mb-1">Cleaned Places</span>
                <span className="text-lg font-bold text-white">
                  {job.quality_report.total_places}
                </span>
                <span className="text-[11px] text-gray-500 block mt-0.5">
                  ({job.quality_report.open_places} open, {job.quality_report.closed_places} closed)
                </span>
              </div>

              <div className="bg-gray-950 p-4 rounded-xl border border-gray-800">
                <span className="text-xs text-gray-500 block mb-1 flex items-center gap-1">
                  <Globe className="w-3.5 h-3.5 text-gray-400" />
                  Real Website
                </span>
                <span className="text-lg font-bold text-emerald-400">
                  {job.quality_report.pct_with_real_website}%
                </span>
                <span className="text-[11px] text-gray-500 block mt-0.5">
                  {job.quality_report.pct_with_website}% any URL
                </span>
              </div>

              <div className="bg-gray-950 p-4 rounded-xl border border-gray-800">
                <span className="text-xs text-gray-500 block mb-1 flex items-center gap-1">
                  <Phone className="w-3.5 h-3.5 text-gray-400" />
                  E.164 Phone
                </span>
                <span className="text-lg font-bold text-white">
                  {job.quality_report.pct_with_phone}%
                </span>
                <span className="text-[11px] text-gray-500 block mt-0.5">Verified format</span>
              </div>

              <div className="bg-gray-950 p-4 rounded-xl border border-gray-800">
                <span className="text-xs text-gray-500 block mb-1 flex items-center gap-1">
                  <Mail className="w-3.5 h-3.5 text-gray-400" />
                  Named Email
                </span>
                <span className="text-lg font-bold text-white">
                  {job.quality_report.pct_with_named_email}%
                </span>
                <span className="text-[11px] text-gray-500 block mt-0.5">
                  {job.quality_report.pct_with_email}% any email
                </span>
              </div>
            </div>

            <div className="flex flex-wrap gap-4 text-xs text-gray-400 pt-2 border-t border-gray-800">
              <span>
                Rating Coverage:{" "}
                <strong className="text-white">{job.quality_report.pct_rating_coverage}%</strong>
              </span>
              <span>•</span>
              <span>
                Duplicates Merged:{" "}
                <strong className="text-white">{job.quality_report.duplicates_removed}</strong>
              </span>
            </div>
          </div>
        )}

        {/* Gap Summary Highlights (when available) */}
        {job.gap_summary && (
          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 sm:p-8 space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-6 h-6 text-indigo-400" />
                <h2 className="text-lg font-bold text-white">Market Gap Insights</h2>
              </div>
              <span className="text-xs text-gray-400">
                Median Area Rating:{" "}
                <strong className="text-white">{job.gap_summary.area_median_rating}★</strong>
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Best Hexes */}
              <div className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Top Opportunity Locations
                </h3>
                <div className="space-y-2">
                  {job.gap_summary.best_hexes.map((hex, idx) => (
                    <div
                      key={hex.h3_index || idx}
                      className="p-3.5 rounded-xl bg-gray-950 border border-emerald-500/20"
                    >
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-xs font-mono text-gray-400">
                          Hex {hex.h3_index.slice(0, 10)}...
                        </span>
                        <span className="text-xs font-bold text-emerald-400">
                          Score {Math.round(hex.opportunity_score)}/100
                        </span>
                      </div>
                      <p className="text-xs text-gray-300">
                        {hex.reasons?.join(" • ") || "High unmet demand"}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Saturated Hexes */}
              <div className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-red-400 flex items-center gap-1.5">
                  <AlertCircle className="w-3.5 h-3.5" />
                  Most Oversaturated Locations
                </h3>
                <div className="space-y-2">
                  {job.gap_summary.saturated_hexes.map((hex, idx) => (
                    <div
                      key={hex.h3_index || idx}
                      className="p-3.5 rounded-xl bg-gray-950 border border-red-500/20"
                    >
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-xs font-mono text-gray-400">
                          Hex {hex.h3_index.slice(0, 10)}...
                        </span>
                        <span className="text-xs font-bold text-red-400">
                          Score {Math.round(hex.opportunity_score)}/100
                        </span>
                      </div>
                      <p className="text-xs text-gray-300">
                        {hex.reasons?.join(" • ") || "Dense competition"}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
