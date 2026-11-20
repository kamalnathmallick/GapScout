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
  AlertCircle,
  HelpCircle,
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
    <div className="min-h-screen bg-gray-950 text-white">
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Navigation & Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <Link
              href="/leads"
              className="text-xs text-gray-400 hover:text-white flex items-center gap-1.5 mb-2 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to All Leads</span>
            </Link>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
              <Brain className="w-6 h-6 text-indigo-400" />
              <span>Active-Learning Queue</span>
            </h1>
            <p className="text-sm text-gray-400 mt-1">
              Surfacing high-uncertainty leads (35%–65% likelihood) and thin-evidence high
              opportunities to maximize model information gain.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/models"
              className="px-3.5 py-2 bg-gray-900 hover:bg-gray-800 border border-gray-800 rounded-lg text-xs font-medium text-gray-300 flex items-center gap-2 transition-colors"
            >
              <TrendingUp className="w-3.5 h-3.5 text-indigo-400" />
              <span>Model Insights</span>
            </Link>
            <button
              onClick={handleRefresh}
              disabled={loading}
              className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-xs font-semibold text-white flex items-center gap-2 transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
              <span>Refresh Queue</span>
            </button>
          </div>
        </div>

        {/* Explainability Banner */}
        <div className="rounded-xl bg-gradient-to-r from-indigo-950/60 to-purple-950/40 border border-indigo-900/60 p-5 space-y-2">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            <h3 className="font-semibold text-sm text-white">Why target these leads next?</h3>
          </div>
          <p className="text-xs text-gray-300 leading-relaxed">
            Conventional outreach focuses purely on high-probability conversions. Active learning
            identifies leads sitting on the classification decision boundary where our model is most
            uncertain. Logging outcomes (replies or non-replies) for these candidates dramatically
            improves classification accuracy with the fewest total contacts.
          </p>
        </div>

        {/* Queue Table */}
        {loading ? (
          <div className="p-12 text-center text-gray-400 text-sm">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto text-indigo-500 mb-3" />
            <span>Scanning leads for active learning opportunities...</span>
          </div>
        ) : error ? (
          <div className="p-6 rounded-xl bg-red-950/40 border border-red-800 text-red-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        ) : leads.length === 0 ? (
          <div className="rounded-xl bg-gray-900 border border-gray-800 p-12 text-center space-y-3">
            <HelpCircle className="w-10 h-10 mx-auto text-gray-600" />
            <h3 className="text-sm font-semibold text-white">
              No active-learning candidates found
            </h3>
            <p className="text-xs text-gray-400 max-w-md mx-auto">
              Run a new scraping analysis to populate fresh uncontacted businesses or wait for new
              leads to enter the pipeline.
            </p>
            <Link
              href="/jobs/new"
              className="inline-block mt-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-xs font-semibold text-white"
            >
              Create New Job
            </Link>
          </div>
        ) : (
          <div className="rounded-xl bg-gray-900 border border-gray-800 overflow-hidden shadow-sm">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-gray-800 bg-gray-950/60 text-gray-400 uppercase font-semibold text-[11px]">
                  <th className="py-3 px-4">Priority & Type</th>
                  <th className="py-3 px-4">Business</th>
                  <th className="py-3 px-4">Rule Score</th>
                  <th className="py-3 px-4">ML Likelihood</th>
                  <th className="py-3 px-4">Active Learning Driver</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60 text-gray-300">
                {leads.map((lead) => (
                  <tr key={lead.lead_id} className="hover:bg-gray-800/40 transition-colors">
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      {lead.learning_priority === "high" ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-indigo-950 border border-indigo-800 text-indigo-300">
                          <Brain className="w-3 h-3" />
                          <span>High Uncertainty</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-950 border border-amber-800 text-amber-300">
                          <Sparkles className="w-3 h-3" />
                          <span>Thin Evidence</span>
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 font-medium text-white">
                      <div className="truncate max-w-xs">{lead.name}</div>
                      <div className="text-[11px] text-gray-500">{lead.category || "General"}</div>
                    </td>
                    <td className="py-3.5 px-4 font-mono font-semibold text-indigo-400">
                      {lead.rule_score !== null ? Math.round(lead.rule_score) : "-"}/100
                    </td>
                    <td className="py-3.5 px-4">
                      {lead.ml_score !== null ? (
                        <span className="font-mono font-semibold text-purple-300 bg-purple-950/60 px-2 py-0.5 rounded border border-purple-800/60">
                          {Math.round(lead.ml_score * 100)}%
                        </span>
                      ) : (
                        <span className="text-gray-500 italic">Rules Only</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-gray-300 max-w-md">
                      <p className="text-[11px] leading-relaxed">{lead.reason}</p>
                    </td>
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <Link
                        href="/leads"
                        className="inline-flex items-center gap-1 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-white rounded text-xs font-medium transition-colors"
                      >
                        <span>View in Leads</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
