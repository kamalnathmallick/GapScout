"use client";

import { useEffect, useState } from "react";
import { Brain, CheckCircle2, Lock, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";

export interface DatasetHealth {
  total_labelled: number;
  positives_count: number;
  negatives_count: number;
  positive_rate: number;
  min_labels_required: number;
  min_positives_required: number;
  unlocked: boolean;
  labels_needed: number;
  positives_needed: number;
}

export function DatasetHealthCard() {
  const [health, setHealth] = useState<DatasetHealth | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchHealth = async () => {
    setLoading(true);
    try {
      const res = await api.getDatasetHealth();
      setHealth(res);
    } catch {
      // Fallback display if not logged in or endpoint unreached
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    async function load() {
      try {
        const res = await api.getDatasetHealth();
        if (!ignore) setHealth(res);
      } catch {
        if (!ignore) setHealth(null);
      } finally {
        if (!ignore) setLoading(false);
      }
    }
    void load();
    return () => {
      ignore = true;
    };
  }, []);

  if (!health && !loading) return null;

  const pctLabels = health
    ? Math.min(100, Math.round((health.total_labelled / health.min_labels_required) * 100))
    : 0;

  return (
    <div className="rounded-xl bg-gray-900 border border-gray-800 p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Brain className="w-5 h-5 text-indigo-400" />
          <h3 className="font-semibold text-white text-sm">ML Lead Scorer Unlock Status</h3>
        </div>
        <div className="flex items-center gap-2">
          {health?.unlocked ? (
            <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950 border border-emerald-800 text-emerald-300">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Model Unlocked</span>
            </span>
          ) : (
            <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-950/60 border border-amber-800 text-amber-300">
              <Lock className="w-3 h-3" />
              <span>Cold-Start Rules Active</span>
            </span>
          )}
          <button
            onClick={fetchHealth}
            disabled={loading}
            className="p-1 rounded text-gray-400 hover:text-white"
            title="Refresh dataset health"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      <p className="text-xs text-gray-400">
        To activate the self-improving ML ranker, log verified outreach outcomes (replies within 14
        days or closed windows).
      </p>

      {/* Metric Counters */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div className="bg-gray-950 p-3 rounded-lg border border-gray-800">
          <span className="text-gray-500 block mb-0.5">Labelled Outcomes</span>
          <span className="text-lg font-bold text-white font-mono">
            {health?.total_labelled ?? 0}
            <span className="text-xs text-gray-500 font-normal">
              {" "}
              / {health?.min_labels_required ?? 150}
            </span>
          </span>
        </div>

        <div className="bg-gray-950 p-3 rounded-lg border border-gray-800">
          <span className="text-gray-500 block mb-0.5">Positive Replies</span>
          <span className="text-lg font-bold text-emerald-400 font-mono">
            {health?.positives_count ?? 0}
            <span className="text-xs text-gray-500 font-normal">
              {" "}
              / {health?.min_positives_required ?? 20}
            </span>
          </span>
        </div>

        <div className="bg-gray-950 p-3 rounded-lg border border-gray-800">
          <span className="text-gray-500 block mb-0.5">Reply Rate</span>
          <span className="text-lg font-bold text-indigo-400 font-mono">
            {health ? (health.positive_rate * 100).toFixed(1) : 0}%
          </span>
        </div>

        <div className="bg-gray-950 p-3 rounded-lg border border-gray-800">
          <span className="text-gray-500 block mb-0.5">Remaining to Unlock</span>
          <span className="text-lg font-bold text-amber-400 font-mono">
            {health?.labels_needed ?? 150} leads
          </span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="space-y-1">
        <div className="flex justify-between text-[11px] text-gray-400">
          <span>Overall Progress</span>
          <span>{pctLabels}%</span>
        </div>
        <div className="w-full bg-gray-950 rounded-full h-2 overflow-hidden border border-gray-800">
          <div
            className={`h-full transition-all duration-500 ${
              health?.unlocked ? "bg-emerald-500" : "bg-indigo-600"
            }`}
            style={{ width: `${pctLabels}%` }}
          />
        </div>
      </div>
    </div>
  );
}
