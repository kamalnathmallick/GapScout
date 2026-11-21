"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Brain,
  Sparkles,
  ArrowLeft,
  RefreshCw,
  ChevronRight,
  TrendingUp,
  Star,
  Zap,
} from "lucide-react";
import { ActiveLearningLeadOut } from "@/lib/types";
import { api } from "@/lib/api";

export default function ActiveLearningPage() {
  const [leads, setLeads] = useState<ActiveLearningLeadOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;
    async function load() {
      try {
        const res = await api.getActiveLearningQueue();
        if (!ignore) {
          setLeads(res || []);
        }
      } catch (err: unknown) {
        if (!ignore) {
          setError(err instanceof Error ? err.message : "Failed to load active learning queue");
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }
    void load();
    return () => {
      ignore = true;
    };
  }, []);

  const handleRefresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getActiveLearningQueue();
      setLeads(res || []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to refresh queue");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 p-6 sm:p-8 max-w-7xl mx-auto w-full space-y-6">
      {/* Navigation & Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800/80">
        <div>
          <Link
            href="/leads"
            className="text-xs text-slate-400 hover:text-white flex items-center gap-1.5 mb-2 transition-colors font-mono"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to All Leads</span>
          </Link>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <Brain className="w-6 h-6 text-indigo-400" />
            <span>Active-Learning Queue</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Surfacing high-uncertainty leads (35%–65% likelihood) and thin-evidence high
            opportunities to maximize model information gain.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Link
            href="/models"
            className="px-3.5 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-xl text-xs font-semibold text-slate-300 flex items-center gap-2 transition-colors"
          >
            <TrendingUp className="w-3.5 h-3.5 text-indigo-400" />
            <span>Model Insights</span>
          </Link>
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-xl text-xs font-semibold text-white flex items-center gap-2 transition-colors shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh Queue</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
          {error}
        </div>
      )}

      {/* Info Callout */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-400 space-y-1.5 leading-relaxed">
        <div className="flex items-center gap-1.5 font-semibold text-slate-200">
          <Zap className="w-4 h-4 text-amber-400" />
          <span>Active Learning Sampling Strategy</span>
        </div>
        <p>
          Instead of contacting predictable leads, prioritizing businesses in the 0.35–0.65
          uncertainty boundary accelerates ML model calibration with minimal labelling effort.
        </p>
      </div>

      {/* Leads Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading ? (
          <div className="col-span-full py-16 text-center text-slate-500">
            <RefreshCw className="w-6 h-6 animate-spin text-indigo-400 mx-auto mb-2" />
            <span className="font-mono text-xs">Evaluating model uncertainty scores...</span>
          </div>
        ) : leads.length === 0 ? (
          <div className="col-span-full glass-panel rounded-2xl p-10 text-center border border-slate-800/80 max-w-md mx-auto space-y-3">
            <Sparkles className="w-8 h-8 text-indigo-400 mx-auto" />
            <h3 className="text-sm font-semibold text-white">Active Learning Queue Empty</h3>
            <p className="text-xs text-slate-400">
              No businesses currently fall in the high-uncertainty band. As new analyses complete,
              novel borderline candidates will automatically appear here.
            </p>
            <Link
              href="/leads"
              className="inline-block px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition-colors"
            >
              Browse All Leads
            </Link>
          </div>
        ) : (
          leads.map((item) => (
            <div
              key={item.lead_id}
              className="glass-panel p-5 rounded-2xl border border-slate-800/80 hover:border-slate-700 transition-all space-y-3 flex flex-col justify-between"
            >
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/25">
                    {item.reason}
                  </span>
                  <div className="flex items-center gap-1 font-mono text-xs text-amber-400">
                    <Star className="w-3.5 h-3.5 fill-amber-400" />
                    <span>{item.rating ? item.rating.toFixed(1) : "--"}</span>
                  </div>
                </div>

                <h3 className="text-sm font-bold text-white truncate">{item.name || "Business"}</h3>
                <p className="text-[11px] text-slate-400 truncate capitalize">
                  {item.category || "General"} • {item.review_count} reviews
                </p>
              </div>

              <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs font-mono">
                <div>
                  <span className="text-slate-500 block text-[10px]">PRIORITY</span>
                  <span className="font-bold text-amber-400 uppercase">
                    {item.learning_priority}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px]">PREDICTED</span>
                  <span className="font-bold text-indigo-400 tabular-nums">
                    {item.ml_score !== null ? `${Math.round(item.ml_score * 100)}%` : "--"}
                  </span>
                </div>
                <Link
                  href={`/leads`}
                  className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold inline-flex items-center gap-1 transition-colors"
                >
                  <span>Review</span>
                  <ChevronRight className="w-3 h-3" />
                </Link>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
