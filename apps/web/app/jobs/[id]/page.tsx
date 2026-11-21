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
      <div className="flex-1 p-8 flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="w-7 h-7 animate-spin text-indigo-400" />
          <p className="text-xs text-slate-400 font-mono">Loading analysis status...</p>
        </div>
      </div>
    );
  }

  if (isError || !job) {
    return (
      <div className="flex-1 p-6 sm:p-8 max-w-4xl mx-auto w-full">
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
          Failed to load job details: {error instanceof Error ? error.message : "Not found"}
        </div>
      </div>
    );
  }

  const isCompleted = job.status === "completed";
  const isRunning =
    job.status === "running" || job.status === "pending" || job.status === "planning";
  const isCanResume = job.status === "paused" || job.status === "cancelled";

  // Visual pipeline stages
  const stages = [
    {
      name: "Scraping Grid",
      done: job.cells_done > 0,
      active: isRunning && job.cells_done < job.cells_total,
    },
    {
      name: "Data Cleaning & Dedupe",
      done: isCompleted || job.cells_done === job.cells_total,
      active: isRunning && job.cells_done === job.cells_total,
    },
    { name: "H3 Gap Engine", done: isCompleted, active: false },
    { name: "Lead Scoring", done: isCompleted, active: false },
  ];

  return (
    <div className="flex-1 p-6 sm:p-8 max-w-5xl mx-auto w-full space-y-8">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-slate-500 mb-1">
            <span>JOB ID</span>
            <span className="text-slate-300">{job.job_id}</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
            <span>Analysis Progress</span>
            {isCompleted ? (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Completed
              </span>
            ) : isRunning ? (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span className="capitalize">{job.status}</span>
              </span>
            ) : (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-800 text-slate-400">
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
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:border-rose-500/30 text-slate-300 hover:text-rose-400 text-xs font-semibold transition-colors"
            >
              <StopCircle className="w-3.5 h-3.5" />
              <span>Cancel</span>
            </button>
          )}

          {isCanResume && (
            <button
              onClick={() => resumeMutation.mutate()}
              disabled={resumeMutation.isPending}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-colors"
            >
              <PlayCircle className="w-3.5 h-3.5" />
              <span>Resume</span>
            </button>
          )}

          {isCompleted && (
            <Link
              href={`/gap/${job.job_id}`}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs sm:text-sm font-semibold transition-all shadow-md shadow-emerald-600/20 hover:scale-[1.01]"
            >
              <span>View Interactive Gap Map</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          )}
        </div>
      </div>

      {/* Visual Pipeline Tracker */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {stages.map((st, i) => (
          <div
            key={st.name}
            className={`p-3 rounded-xl border text-xs flex items-center gap-2.5 transition-colors ${
              st.done
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                : st.active
                  ? "bg-indigo-500/10 border-indigo-500/30 text-indigo-300"
                  : "bg-slate-950/60 border-slate-800 text-slate-500"
            }`}
          >
            <div
              className={`w-5 h-5 rounded-full flex items-center justify-center font-mono text-[10px] font-bold ${
                st.done
                  ? "bg-emerald-500/20 text-emerald-400"
                  : st.active
                    ? "bg-indigo-500/20 text-indigo-400 animate-pulse"
                    : "bg-slate-800 text-slate-500"
              }`}
            >
              {st.done ? "✓" : i + 1}
            </div>
            <span className="truncate font-medium">{st.name}</span>
          </div>
        ))}
      </div>

      {/* Live Progress Bar Card */}
      <div className="glass-panel rounded-2xl p-6 sm:p-8 space-y-6 border border-slate-800/80">
        <div>
          <div className="flex justify-between items-center text-xs mb-2">
            <span className="text-slate-400 font-medium flex items-center gap-2">
              <span>Coverage Grid Execution</span>
              {isRunning && (
                <span className="text-[11px] text-indigo-400 font-mono">(Polling every 3s)</span>
              )}
            </span>
            <span className="font-mono text-white font-bold tabular-nums text-sm">
              {job.pct_complete} %
            </span>
          </div>
          <div className="w-full bg-slate-950 rounded-full h-3 overflow-hidden border border-slate-800 p-0.5">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                isCompleted ? "bg-emerald-500" : "bg-indigo-500"
              }`}
              style={{ width: `${Math.max(job.pct_complete, 2)}%` }}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-1">
          <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-3.5">
            <span className="text-[11px] text-slate-500 block mb-1">Cells Done / Total</span>
            <span className="text-lg font-bold font-mono text-white tabular-nums">
              {job.cells_done} / {job.cells_total}
            </span>
          </div>

          <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-3.5">
            <span className="text-[11px] text-slate-500 block mb-1">Places Found</span>
            <span className="text-lg font-bold font-mono text-indigo-400 tabular-nums">
              {job.places_found}
            </span>
          </div>

          <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-3.5">
            <span className="text-[11px] text-slate-500 block mb-1">Errors</span>
            <span
              className={`text-lg font-bold font-mono tabular-nums ${
                job.errors_count > 0 ? "text-rose-400" : "text-slate-400"
              }`}
            >
              {job.errors_count}
            </span>
          </div>

          <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-3.5">
            <span className="text-[11px] text-slate-500 block mb-1">Status</span>
            <span className="text-sm font-semibold capitalize text-slate-200">{job.status}</span>
          </div>
        </div>
      </div>

      {/* Quality Report (when available) */}
      {job.quality_report && (
        <div className="glass-panel rounded-2xl p-6 sm:p-8 space-y-6 border border-slate-800/80">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            <h2 className="text-base font-bold text-white">Data Quality Report</h2>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-slate-950/80 p-3.5 rounded-xl border border-slate-800">
              <span className="text-[11px] text-slate-500 block mb-1">Cleaned Places</span>
              <span className="text-lg font-bold text-white tabular-nums">
                {job.quality_report.total_places}
              </span>
              <span className="text-[10px] text-slate-500 block mt-0.5 font-mono">
                ({job.quality_report.open_places} open, {job.quality_report.closed_places} closed)
              </span>
            </div>

            <div className="bg-slate-950/80 p-3.5 rounded-xl border border-slate-800">
              <span className="text-[11px] text-slate-500 block mb-1 flex items-center gap-1">
                <Globe className="w-3 h-3 text-slate-400" />
                Real Website
              </span>
              <span className="text-lg font-bold text-emerald-400 tabular-nums">
                {job.quality_report.pct_with_real_website}%
              </span>
              <span className="text-[10px] text-slate-500 block mt-0.5 font-mono">
                {job.quality_report.pct_with_website}% any URL
              </span>
            </div>

            <div className="bg-slate-950/80 p-3.5 rounded-xl border border-slate-800">
              <span className="text-[11px] text-slate-500 block mb-1 flex items-center gap-1">
                <Phone className="w-3 h-3 text-slate-400" />
                E.164 Phone
              </span>
              <span className="text-lg font-bold text-white tabular-nums">
                {job.quality_report.pct_with_phone}%
              </span>
              <span className="text-[10px] text-slate-500 block mt-0.5 font-mono">
                Verified format
              </span>
            </div>

            <div className="bg-slate-950/80 p-3.5 rounded-xl border border-slate-800">
              <span className="text-[11px] text-slate-500 block mb-1 flex items-center gap-1">
                <Mail className="w-3 h-3 text-slate-400" />
                Named Email
              </span>
              <span className="text-lg font-bold text-white tabular-nums">
                {job.quality_report.pct_with_named_email}%
              </span>
              <span className="text-[10px] text-slate-500 block mt-0.5 font-mono">
                {job.quality_report.pct_with_email}% any email
              </span>
            </div>
          </div>

          <div className="flex flex-wrap gap-4 text-xs text-slate-400 pt-2 border-t border-slate-800 font-mono">
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
        <div className="glass-panel rounded-2xl p-6 sm:p-8 space-y-6 border border-slate-800/80">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-indigo-400" />
              <h2 className="text-base font-bold text-white">Market Gap Insights</h2>
            </div>
            <span className="text-xs text-slate-400 font-mono">
              Median Area Rating:{" "}
              <strong className="text-white">{job.gap_summary.area_median_rating}★</strong>
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Best Hexes */}
            <div className="space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5 font-mono">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Top Opportunity Locations
              </h3>
              <div className="space-y-2">
                {job.gap_summary.best_hexes.map((hex, idx) => (
                  <div
                    key={hex.h3_index || idx}
                    className="p-3.5 rounded-xl bg-slate-950/80 border border-emerald-500/25"
                  >
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-xs font-mono text-slate-400">
                        Hex {hex.h3_index.slice(0, 10)}...
                      </span>
                      <span className="text-xs font-bold text-emerald-400 font-mono tabular-nums">
                        Score {Math.round(hex.opportunity_score)}/100
                      </span>
                    </div>
                    <p className="text-xs text-slate-300">
                      {hex.reasons?.join(" • ") || "High unmet demand"}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Saturated Hexes */}
            <div className="space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-rose-400 flex items-center gap-1.5 font-mono">
                <AlertCircle className="w-3.5 h-3.5" />
                Most Oversaturated Locations
              </h3>
              <div className="space-y-2">
                {job.gap_summary.saturated_hexes.map((hex, idx) => (
                  <div
                    key={hex.h3_index || idx}
                    className="p-3.5 rounded-xl bg-slate-950/80 border border-rose-500/25"
                  >
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-xs font-mono text-slate-400">
                        Hex {hex.h3_index.slice(0, 10)}...
                      </span>
                      <span className="text-xs font-bold text-rose-400 font-mono tabular-nums">
                        Score {Math.round(hex.opportunity_score)}/100
                      </span>
                    </div>
                    <p className="text-xs text-slate-300">
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
  );
}
