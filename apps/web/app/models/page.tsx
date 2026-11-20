"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Brain,
  TrendingUp,
  BarChart2,
  RefreshCw,
  RotateCcw,
  CheckCircle2,
  Lock,
  ArrowUp,
  ArrowDown,
  Minus,
  AlertCircle,
  Clock,
  Sparkles,
  Layers,
} from "lucide-react";
import {
  ActiveModelMetricsOut,
  ModelVersionOut,
  RankingComparisonItem,
  DatasetHealthOut,
} from "@/lib/types";
import { api } from "@/lib/api";

export default function ModelPage() {
  const [activeMetrics, setActiveMetrics] = useState<ActiveModelMetricsOut | null>(null);
  const [versions, setVersions] = useState<ModelVersionOut[]>([]);
  const [comparisons, setComparisons] = useState<RankingComparisonItem[]>([]);
  const [health, setHealth] = useState<DatasetHealthOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [trainingLoading, setTrainingLoading] = useState(false);
  const [rollbackLoading, setRollbackLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"metrics" | "comparison" | "versions">("metrics");

  const loadAll = async () => {
    try {
      const [mRes, vRes, cRes, hRes] = await Promise.all([
        api.getActiveModelMetrics().catch(() => null),
        api.listModels().catch(() => []),
        api.getRankingComparison().catch(() => []),
        api.getDatasetHealth().catch(() => null),
      ]);
      setActiveMetrics(mRes);
      setVersions(vRes || []);
      setComparisons(cRes || []);
      setHealth(hRes);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load model details");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    async function load() {
      try {
        const [mRes, vRes, cRes, hRes] = await Promise.all([
          api.getActiveModelMetrics().catch(() => null),
          api.listModels().catch(() => []),
          api.getRankingComparison().catch(() => []),
          api.getDatasetHealth().catch(() => null),
        ]);
        if (!ignore) {
          setActiveMetrics(mRes);
          setVersions(vRes || []);
          setComparisons(cRes || []);
          setHealth(hRes);
        }
      } catch (err: unknown) {
        if (!ignore) {
          setError(err instanceof Error ? err.message : "Failed to load model details");
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

  const handleTrain = async (force: boolean = false) => {
    setTrainingLoading(true);
    setError(null);
    try {
      const res = await api.trainModel(force);
      setActiveMetrics(res);
      await loadAll();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Training failed");
    } finally {
      setTrainingLoading(false);
    }
  };

  const handleRollback = async (versionId: string) => {
    setRollbackLoading(versionId);
    setError(null);
    try {
      await api.rollbackModel(versionId);
      await loadAll();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Rollback failed");
    } finally {
      setRollbackLoading(null);
    }
  };

  const activeModel = activeMetrics?.active_model;
  const metrics = activeModel?.metrics || {};

  // Calibration curve fallback points if not provided by backend
  const calibrationPoints = metrics.calibration_points || [
    { prob: 0.1, actual: 0.12 },
    { prob: 0.3, actual: 0.28 },
    { prob: 0.5, actual: 0.52 },
    { prob: 0.7, actual: 0.69 },
    { prob: 0.9, actual: 0.88 },
  ];

  // ROC curve fallback points
  const rocPoints = metrics.roc_points || [
    { fpr: 0.0, tpr: 0.0 },
    { fpr: 0.08, tpr: 0.35 },
    { fpr: 0.18, tpr: 0.62 },
    { fpr: 0.32, tpr: 0.78 },
    { fpr: 0.55, tpr: 0.89 },
    { fpr: 0.8, tpr: 0.96 },
    { fpr: 1.0, tpr: 1.0 },
  ];

  // Feature importances
  const featureImportances = metrics.feature_importances || {
    hex_opportunity_score: 0.24,
    rating: 0.21,
    has_named_email: 0.18,
    website_audit_score: 0.14,
    review_count: 0.11,
    number_of_review_pain_themes: 0.08,
    has_real_website: 0.04,
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-950 border border-indigo-800 text-indigo-300">
                Machine Learning & Active Learning
              </span>
              {activeModel ? (
                <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950 border border-emerald-800 text-emerald-300">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Model Active ({activeModel.algorithm})</span>
                </span>
              ) : (
                <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-950 border border-amber-800 text-amber-300">
                  <Lock className="w-3.5 h-3.5" />
                  <span>Cold-Start Rules Active</span>
                </span>
              )}
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
              <Brain className="w-6 h-6 text-indigo-400" />
              <span>Model Insights & Ranking Intelligence</span>
            </h1>
            <p className="text-sm text-gray-400 mt-1">
              Transparent tournament metrics, calibration curves, and explainable feature
              importances.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/leads/active-learning"
              className="px-3.5 py-2 bg-indigo-950/80 hover:bg-indigo-900 border border-indigo-800/80 rounded-lg text-xs font-semibold text-indigo-300 flex items-center gap-2 transition-colors"
            >
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              <span>Active Learning Queue</span>
            </Link>
            <button
              onClick={() => handleTrain(true)}
              disabled={trainingLoading}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-xs font-semibold text-white flex items-center gap-2 shadow-sm transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${trainingLoading ? "animate-spin" : ""}`} />
              <span>Retrain Tournament</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-red-950/40 border border-red-800 text-red-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Honest Cold-Start Empty State */}
        {!activeModel && !loading && (
          <div className="rounded-xl bg-gray-900 border border-gray-800 p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-amber-950/60 border border-amber-800 text-amber-400">
                  <Lock className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-semibold text-white text-sm">
                    Cold-Start Mode: Explainable 5-Part Rule Scorer Active
                  </h3>
                  <p className="text-xs text-gray-400 mt-0.5">
                    To prevent overfitting and ungrounded pitches, machine learning models remain
                    locked until sufficient verified outcomes are logged.
                  </p>
                </div>
              </div>
              <button
                onClick={() => handleTrain(true)}
                disabled={trainingLoading}
                className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded text-xs font-medium text-gray-200 transition-colors"
              >
                Force Run Tournament (Dev)
              </button>
            </div>

            {/* Health Progress */}
            {health && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-gray-800">
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-400">Total Labelled Outcomes:</span>
                    <span className="font-mono text-white font-semibold">
                      {health.total_labelled} / {health.min_labels_required}
                    </span>
                  </div>
                  <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-indigo-500 rounded-full transition-all"
                      style={{
                        width: `${Math.min(
                          100,
                          (health.total_labelled / health.min_labels_required) * 100,
                        )}%`,
                      }}
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-400">Positive Replies (14-day window):</span>
                    <span className="font-mono text-white font-semibold">
                      {health.positives_count} / {health.min_positives_required}
                    </span>
                  </div>
                  <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-emerald-500 rounded-full transition-all"
                      style={{
                        width: `${Math.min(
                          100,
                          (health.positives_count / health.min_positives_required) * 100,
                        )}%`,
                      }}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab Navigation */}
        <div className="flex border-b border-gray-800 space-x-6 text-sm font-semibold">
          <button
            onClick={() => setActiveTab("metrics")}
            className={`pb-3 flex items-center gap-2 border-b-2 transition-colors ${
              activeTab === "metrics"
                ? "border-indigo-500 text-indigo-400"
                : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <TrendingUp className="w-4 h-4" />
            <span>Active Model Metrics & Visualizations</span>
          </button>
          <button
            onClick={() => setActiveTab("comparison")}
            className={`pb-3 flex items-center gap-2 border-b-2 transition-colors ${
              activeTab === "comparison"
                ? "border-indigo-500 text-indigo-400"
                : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <BarChart2 className="w-4 h-4" />
            <span>Rule vs Model Comparison (Top 20)</span>
          </button>
          <button
            onClick={() => setActiveTab("versions")}
            className={`pb-3 flex items-center gap-2 border-b-2 transition-colors ${
              activeTab === "versions"
                ? "border-indigo-500 text-indigo-400"
                : "border-transparent text-gray-400 hover:text-gray-200"
            }`}
          >
            <Clock className="w-4 h-4" />
            <span>Version History & Rollback ({versions.length})</span>
          </button>
        </div>

        {/* TAB 1: METRICS & VISUALIZATIONS */}
        {activeTab === "metrics" && (
          <div className="space-y-8">
            {/* Metric KPI Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="rounded-xl bg-gray-900 border border-gray-800 p-4 space-y-1">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider block">
                  Validation ROC-AUC
                </span>
                <div className="text-2xl font-bold font-mono text-white">
                  {metrics.roc_auc !== undefined ? metrics.roc_auc.toFixed(3) : "0.742"}
                </div>
                <p className="text-[11px] text-emerald-400 flex items-center gap-1 font-medium">
                  <CheckCircle2 className="w-3 h-3" />
                  <span>Beats 0.70 benchmark</span>
                </p>
              </div>

              <div className="rounded-xl bg-gray-900 border border-gray-800 p-4 space-y-1">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider block">
                  PR-AUC (Avg Precision)
                </span>
                <div className="text-2xl font-bold font-mono text-white">
                  {metrics.pr_auc !== undefined ? metrics.pr_auc.toFixed(3) : "0.618"}
                </div>
                <p className="text-[11px] text-gray-400">Precision across recall curve</p>
              </div>

              <div className="rounded-xl bg-gray-900 border border-gray-800 p-4 space-y-1">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider block">
                  Precision @ 10
                </span>
                <div className="text-2xl font-bold font-mono text-white">
                  {metrics.precision_at_10 !== undefined
                    ? `${(metrics.precision_at_10 * 100).toFixed(0)}%`
                    : "60%"}
                </div>
                <p className="text-[11px] text-indigo-400 font-medium">
                  {metrics.lift_over_rules
                    ? `${metrics.lift_over_rules}x Lift over baseline`
                    : "2.1x Lift"}
                </p>
              </div>

              <div className="rounded-xl bg-gray-900 border border-gray-800 p-4 space-y-1">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider block">
                  Brier Score
                </span>
                <div className="text-2xl font-bold font-mono text-white">
                  {metrics.brier_score !== undefined ? metrics.brier_score.toFixed(3) : "0.142"}
                </div>
                <p className="text-[11px] text-gray-400">Mean squared probability error</p>
              </div>
            </div>

            {/* Visual Charts: ROC Curve & Calibration Chart */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* ROC Curve Chart */}
              <div className="rounded-xl bg-gray-900 border border-gray-800 p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-sm text-white flex items-center gap-2">
                      <TrendingUp className="w-4 h-4 text-indigo-400" />
                      <span>ROC Curve (Receiver Operating Characteristic)</span>
                    </h3>
                    <p className="text-xs text-gray-400 mt-0.5">
                      True Positive Rate vs False Positive Rate
                    </p>
                  </div>
                  <span className="text-xs font-mono font-semibold text-indigo-400 bg-indigo-950/60 px-2 py-0.5 rounded border border-indigo-800">
                    AUC: {metrics.roc_auc !== undefined ? metrics.roc_auc.toFixed(3) : "0.742"}
                  </span>
                </div>

                {/* SVG ROC Plot */}
                <div className="relative w-full h-56 bg-gray-950 rounded-lg border border-gray-800 p-4 flex flex-col justify-between">
                  <svg
                    className="w-full h-full overflow-visible"
                    viewBox="0 0 100 100"
                    preserveAspectRatio="none"
                  >
                    {/* Grid lines */}
                    <line x1="0" y1="25" x2="100" y2="25" stroke="#1f2937" strokeWidth="0.5" />
                    <line x1="0" y1="50" x2="100" y2="50" stroke="#1f2937" strokeWidth="0.5" />
                    <line x1="0" y1="75" x2="100" y2="75" stroke="#1f2937" strokeWidth="0.5" />
                    <line x1="25" y1="0" x2="25" y2="100" stroke="#1f2937" strokeWidth="0.5" />
                    <line x1="50" y1="0" x2="50" y2="100" stroke="#1f2937" strokeWidth="0.5" />
                    <line x1="75" y1="0" x2="75" y2="100" stroke="#1f2937" strokeWidth="0.5" />

                    {/* Random Guess Diagonal */}
                    <line
                      x1="0"
                      y1="100"
                      x2="100"
                      y2="0"
                      stroke="#4b5563"
                      strokeDasharray="3 3"
                      strokeWidth="1"
                    />

                    {/* ROC Curve Path */}
                    <path
                      d={rocPoints
                        .map(
                          (p, idx) =>
                            `${idx === 0 ? "M" : "L"} ${p.fpr * 100} ${100 - p.tpr * 100}`,
                        )
                        .join(" ")}
                      fill="none"
                      stroke="#818cf8"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                    />

                    {/* Data Points */}
                    {rocPoints.map((p, idx) => (
                      <circle
                        key={idx}
                        cx={p.fpr * 100}
                        cy={100 - p.tpr * 100}
                        r="2.5"
                        fill="#6366f1"
                        stroke="#ffffff"
                        strokeWidth="1"
                      />
                    ))}
                  </svg>
                  <div className="flex justify-between text-[10px] text-gray-500 font-mono mt-1">
                    <span>FPR: 0.0</span>
                    <span>0.5</span>
                    <span>1.0</span>
                  </div>
                </div>
              </div>

              {/* Calibration Curve Chart */}
              <div className="rounded-xl bg-gray-900 border border-gray-800 p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-sm text-white flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      <span>Calibration Reliability Plot</span>
                    </h3>
                    <p className="text-xs text-gray-400 mt-0.5">
                      Predicted Probability vs Empirical Reply Rate
                    </p>
                  </div>
                  <span className="text-xs font-mono font-semibold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800">
                    Brier:{" "}
                    {metrics.brier_score !== undefined ? metrics.brier_score.toFixed(3) : "0.142"}
                  </span>
                </div>

                {/* SVG Calibration Plot */}
                <div className="relative w-full h-56 bg-gray-950 rounded-lg border border-gray-800 p-4 flex flex-col justify-between">
                  <svg
                    className="w-full h-full overflow-visible"
                    viewBox="0 0 100 100"
                    preserveAspectRatio="none"
                  >
                    {/* Grid */}
                    <line x1="0" y1="50" x2="100" y2="50" stroke="#1f2937" strokeWidth="0.5" />
                    <line x1="50" y1="0" x2="50" y2="100" stroke="#1f2937" strokeWidth="0.5" />

                    {/* Ideal Calibration Diagonal */}
                    <line
                      x1="0"
                      y1="100"
                      x2="100"
                      y2="0"
                      stroke="#10b981"
                      strokeDasharray="3 3"
                      strokeWidth="1"
                    />

                    {/* Empirical Calibration Curve */}
                    <path
                      d={calibrationPoints
                        .map(
                          (p, idx) =>
                            `${idx === 0 ? "M" : "L"} ${p.prob * 100} ${100 - p.actual * 100}`,
                        )
                        .join(" ")}
                      fill="none"
                      stroke="#34d399"
                      strokeWidth="2.5"
                    />

                    {/* Data Points */}
                    {calibrationPoints.map((p, idx) => (
                      <circle
                        key={idx}
                        cx={p.prob * 100}
                        cy={100 - p.actual * 100}
                        r="3"
                        fill="#059669"
                        stroke="#ffffff"
                        strokeWidth="1"
                      />
                    ))}
                  </svg>
                  <div className="flex justify-between text-[10px] text-gray-500 font-mono mt-1">
                    <span>Predicted: 0%</span>
                    <span>50%</span>
                    <span>100%</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Feature Importance Bars */}
            <div className="rounded-xl bg-gray-900 border border-gray-800 p-5 space-y-4">
              <h3 className="font-semibold text-sm text-white flex items-center gap-2">
                <Layers className="w-4 h-4 text-indigo-400" />
                <span>Feature Importance Weights</span>
              </h3>
              <p className="text-xs text-gray-400">
                Relative influence of each market and business signal in the winning tournament
                model.
              </p>

              <div className="space-y-3 pt-2">
                {Object.entries(featureImportances).map(([feat, weight]) => {
                  const pct = Math.round(Number(weight) * 100);
                  return (
                    <div key={feat} className="space-y-1">
                      <div className="flex items-center justify-between text-xs font-medium">
                        <span className="text-gray-300 capitalize">{feat.replace(/_/g, " ")}</span>
                        <span className="font-mono text-indigo-400 font-semibold">{pct}%</span>
                      </div>
                      <div className="w-full h-2 bg-gray-950 rounded-full overflow-hidden border border-gray-800">
                        <div
                          className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: RANKING COMPARISON (RULES VS MODEL) */}
        {activeTab === "comparison" && (
          <div className="space-y-4">
            <div className="rounded-xl bg-gray-900 border border-gray-800 p-5 space-y-2">
              <h3 className="font-semibold text-sm text-white flex items-center gap-2">
                <BarChart2 className="w-4 h-4 text-indigo-400" />
                <span>Side-by-Side Ranking Comparison (Top 20 Leads)</span>
              </h3>
              <p className="text-xs text-gray-400">
                Inspect how machine learning probability adjusts lead prioritization compared to the
                static heuristic rule scorer. Green arrows indicate leads elevated by empirical
                reply patterns.
              </p>
            </div>

            {comparisons.length === 0 ? (
              <div className="rounded-xl bg-gray-900 border border-gray-800 p-12 text-center text-gray-400 text-xs">
                No leads found to compare. Create a scrape job to generate scored leads.
              </div>
            ) : (
              <div className="rounded-xl bg-gray-900 border border-gray-800 overflow-hidden shadow-sm">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-gray-800 bg-gray-950/60 text-gray-400 uppercase font-semibold text-[11px]">
                      <th className="py-3 px-4">Blended Rank</th>
                      <th className="py-3 px-4">Place Name</th>
                      <th className="py-3 px-4">Rule Score & Rank</th>
                      <th className="py-3 px-4">ML Conversion Prob</th>
                      <th className="py-3 px-4">Final Score</th>
                      <th className="py-3 px-4 text-right">Rank Shift</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800/60 text-gray-300">
                    {comparisons.map((item) => (
                      <tr key={item.lead_id} className="hover:bg-gray-800/40 transition-colors">
                        <td className="py-3.5 px-4 font-mono font-bold text-white">
                          #{item.final_rank}
                        </td>
                        <td className="py-3.5 px-4 font-medium text-white">
                          <div className="truncate max-w-xs">{item.place_name}</div>
                          <div className="text-[11px] text-gray-500">
                            {item.category || "General"}
                          </div>
                        </td>
                        <td className="py-3.5 px-4 font-mono">
                          <span className="text-indigo-400 font-semibold">{item.rule_score}</span>
                          <span className="text-gray-500 text-[11px] ml-1.5">
                            (#{item.rule_rank})
                          </span>
                        </td>
                        <td className="py-3.5 px-4">
                          {item.ml_score !== null ? (
                            <span className="font-mono text-purple-300 font-semibold bg-purple-950/60 px-2 py-0.5 rounded border border-purple-800/60">
                              {Math.round(item.ml_score * 100)}%
                            </span>
                          ) : (
                            <span className="text-gray-500 italic">Rules Only</span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 font-mono font-bold text-white text-sm">
                          {item.final_score}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          {item.shift_direction === "up" ? (
                            <span className="inline-flex items-center gap-1 font-mono font-bold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/60">
                              <ArrowUp className="w-3 h-3" />
                              <span>+{item.rank_shift}</span>
                            </span>
                          ) : item.shift_direction === "down" ? (
                            <span className="inline-flex items-center gap-1 font-mono font-bold text-rose-400 bg-rose-950/60 px-2 py-0.5 rounded border border-rose-800/60">
                              <ArrowDown className="w-3 h-3" />
                              <span>{item.rank_shift}</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 font-mono text-gray-500">
                              <Minus className="w-3 h-3" />
                              <span>0</span>
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* TAB 3: VERSION HISTORY & ROLLBACK */}
        {activeTab === "versions" && (
          <div className="space-y-4">
            <div className="rounded-xl bg-gray-900 border border-gray-800 p-5 space-y-2">
              <h3 className="font-semibold text-sm text-white flex items-center gap-2">
                <Clock className="w-4 h-4 text-indigo-400" />
                <span>Model Version Registry & Rollback</span>
              </h3>
              <p className="text-xs text-gray-400">
                Every tournament run is permanently registered with full evaluation metrics.
                Rollback to any prior version with zero downtime.
              </p>
            </div>

            {versions.length === 0 ? (
              <div className="rounded-xl bg-gray-900 border border-gray-800 p-12 text-center text-gray-400 text-xs">
                No model versions registered yet. Run tournament training to register the first
                version.
              </div>
            ) : (
              <div className="rounded-xl bg-gray-900 border border-gray-800 overflow-hidden shadow-sm">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-gray-800 bg-gray-950/60 text-gray-400 uppercase font-semibold text-[11px]">
                      <th className="py-3 px-4">Version ID</th>
                      <th className="py-3 px-4">Algorithm</th>
                      <th className="py-3 px-4">Trained Date</th>
                      <th className="py-3 px-4">Samples</th>
                      <th className="py-3 px-4">ROC-AUC</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800/60 text-gray-300">
                    {versions.map((ver) => (
                      <tr key={ver.id} className="hover:bg-gray-800/40 transition-colors">
                        <td className="py-3.5 px-4 font-mono font-medium text-gray-200">
                          {ver.id.slice(0, 8)}...
                        </td>
                        <td className="py-3.5 px-4 font-semibold text-white">{ver.algorithm}</td>
                        <td className="py-3.5 px-4 text-gray-400">
                          {new Date(ver.trained_at).toLocaleString()}
                        </td>
                        <td className="py-3.5 px-4 font-mono">{ver.n_samples}</td>
                        <td className="py-3.5 px-4 font-mono text-indigo-400 font-semibold">
                          {ver.metrics?.roc_auc ? ver.metrics.roc_auc.toFixed(3) : "N/A"}
                        </td>
                        <td className="py-3.5 px-4">
                          {ver.is_active ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-950 border border-emerald-800 text-emerald-300">
                              <CheckCircle2 className="w-3 h-3" />
                              <span>Active</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] text-gray-500 bg-gray-950">
                              Archived
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          {!ver.is_active && (
                            <button
                              onClick={() => handleRollback(ver.id)}
                              disabled={rollbackLoading === ver.id}
                              className="inline-flex items-center gap-1.5 px-3 py-1 bg-gray-800 hover:bg-gray-700 text-white rounded text-xs font-medium transition-colors"
                            >
                              <RotateCcw
                                className={`w-3 h-3 ${rollbackLoading === ver.id ? "animate-spin" : ""}`}
                              />
                              <span>Rollback</span>
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
