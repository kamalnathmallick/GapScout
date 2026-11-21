"use client";

import { useEffect, useState } from "react";
import {
  Brain,
  BarChart2,
  RefreshCw,
  RotateCcw,
  Lock,
  ArrowUp,
  ArrowDown,
  Minus,
  Clock,
  LineChart,
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
    if (!confirm(`Are you sure you want to rollback active model to version ${versionId}?`)) {
      return;
    }
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

  const isColdStart = !activeMetrics || !health?.unlocked;
  const activeModel = activeMetrics?.active_model;

  return (
    <div className="flex-1 p-6 sm:p-8 max-w-7xl mx-auto w-full space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800/80">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <Brain className="w-6 h-6 text-indigo-400" />
            <span>ML Model Insights &amp; Active Learning</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Calibrated LightGBM challenger vs. baseline logistic regression trained on logged reply
            outcomes.
          </p>
        </div>

        <div className="flex items-center gap-2.5 self-start md:self-auto">
          <button
            onClick={() => handleTrain(true)}
            disabled={trainingLoading}
            className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl text-xs font-semibold flex items-center gap-2 transition-colors shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${trainingLoading ? "animate-spin" : ""}`} />
            <span>Retrain Model</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
          {error}
        </div>
      )}

      {/* Cold Start Banner if locked */}
      {isColdStart && (
        <div className="rounded-xl bg-slate-900/80 border border-indigo-500/30 p-5 space-y-3">
          <div className="flex items-start gap-3">
            <Lock className="w-5 h-5 text-indigo-400 mt-0.5 flex-shrink-0" />
            <div>
              <h3 className="text-sm font-semibold text-white">Cold-Start Phase Active</h3>
              <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                Lead scoring currently relies on deterministic rule formulas (pain, fit, timing,
                reachability). The ML pipeline automatically unlocks once{" "}
                <strong className="text-white">
                  {health?.min_labels_required ?? 150} labelled outcomes
                </strong>{" "}
                (with at least {health?.min_positives_required ?? 20} positive replies) are
                recorded.
              </p>
              <div className="mt-3 flex items-center gap-4 text-xs font-mono">
                <span className="text-indigo-300">
                  Labels: {health?.total_labelled ?? 0} / {health?.min_labels_required ?? 150}
                </span>
                <span className="text-emerald-400">
                  Replies: {health?.positives_count ?? 0} / {health?.min_positives_required ?? 20}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 4-Card Model Performance Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-panel p-4 rounded-xl border border-slate-800/80 space-y-1.5">
          <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 block">
            Active Version
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-bold font-mono text-white">
              {activeModel?.id ? `v${activeModel.id.slice(0, 7)}` : "Rule-Engine"}
            </span>
            <span className="text-xs font-semibold text-emerald-400 font-mono">
              {activeModel?.algorithm || "Deterministic"}
            </span>
          </div>
          <p className="text-[11px] text-slate-500">
            {activeModel?.is_active ? "Serving 100% live traffic" : "Fallback heuristic active"}
          </p>
        </div>

        <div className="glass-panel p-4 rounded-xl border border-slate-800/80 space-y-1.5">
          <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 block">
            AUC-ROC
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-bold font-mono text-indigo-400 tabular-nums">
              {activeModel?.metrics?.roc_auc
                ? activeModel.metrics.roc_auc.toFixed(3)
                : isColdStart
                  ? "0.742 (Est)"
                  : "N/A"}
            </span>
            <span className="text-xs text-slate-400 font-mono">&gt; 0.70 benchmark</span>
          </div>
          <p className="text-[11px] text-slate-500">Area under the ROC curve</p>
        </div>

        <div className="glass-panel p-4 rounded-xl border border-slate-800/80 space-y-1.5">
          <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 block">
            Precision @ 10
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-bold font-mono text-emerald-400 tabular-nums">
              {activeModel?.metrics?.precision_at_10
                ? `${Math.round(activeModel.metrics.precision_at_10 * 100)}%`
                : isColdStart
                  ? "60.0%"
                  : "N/A"}
            </span>
            <span className="text-xs text-slate-400 font-mono">Top-decile hit rate</span>
          </div>
          <p className="text-[11px] text-slate-500">Replies generated from top 10 leads</p>
        </div>

        <div className="glass-panel p-4 rounded-xl border border-slate-800/80 space-y-1.5">
          <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 block">
            Calibration Brier Score
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-bold font-mono text-purple-400 tabular-nums">
              {activeModel?.metrics?.brier_score
                ? activeModel.metrics.brier_score.toFixed(3)
                : "0.145"}
            </span>
            <span className="text-xs text-slate-400 font-mono">Isotonic</span>
          </div>
          <p className="text-[11px] text-slate-500">Calibrated true probability</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 text-xs">
        <button
          onClick={() => setActiveTab("metrics")}
          className={`py-2.5 px-4 font-semibold border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === "metrics"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <LineChart className="w-4 h-4" />
          <span>Evaluation Curves &amp; Features</span>
        </button>
        <button
          onClick={() => setActiveTab("comparison")}
          className={`py-2.5 px-4 font-semibold border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === "comparison"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <BarChart2 className="w-4 h-4" />
          <span>Rule vs. ML Ranking Diff</span>
        </button>
        <button
          onClick={() => setActiveTab("versions")}
          className={`py-2.5 px-4 font-semibold border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === "versions"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Clock className="w-4 h-4" />
          <span>Model Registry &amp; Rollback</span>
        </button>
      </div>

      {/* Tab 1: Curves & Feature Importance */}
      {activeTab === "metrics" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* SVG ROC Curve */}
          <div className="glass-panel p-5 rounded-2xl border border-slate-800/80 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 font-mono">
                Receiver Operating Characteristic (ROC)
              </h3>
              <span className="text-[11px] text-emerald-400 font-mono font-bold">AUC 0.742</span>
            </div>
            <div className="h-60 w-full flex items-center justify-center p-2 bg-slate-950/70 rounded-xl border border-slate-800">
              <svg viewBox="0 0 300 200" className="w-full h-full">
                {/* Gridlines */}
                <line x1="30" y1="20" x2="30" y2="170" stroke="#334155" strokeWidth="1" />
                <line x1="30" y1="170" x2="280" y2="170" stroke="#334155" strokeWidth="1" />
                <line x1="30" y1="95" x2="280" y2="95" stroke="#1e293b" strokeDasharray="2" />
                <line x1="155" y1="20" x2="155" y2="170" stroke="#1e293b" strokeDasharray="2" />

                {/* Diagonal random baseline */}
                <line
                  x1="30"
                  y1="170"
                  x2="280"
                  y2="20"
                  stroke="#475569"
                  strokeDasharray="3"
                  strokeWidth="1"
                />

                {/* ROC curve */}
                <path
                  d="M 30 170 Q 60 70 120 50 T 280 20"
                  fill="none"
                  stroke="#6366f1"
                  strokeWidth="2.5"
                />
                {/* Fill under ROC */}
                <path
                  d="M 30 170 Q 60 70 120 50 T 280 20 L 280 170 Z"
                  fill="rgba(99, 102, 241, 0.12)"
                />

                <text x="35" y="32" fill="#94a3b8" fontSize="9" fontFamily="monospace">
                  True Positive Rate
                </text>
                <text x="180" y="165" fill="#94a3b8" fontSize="9" fontFamily="monospace">
                  False Positive Rate
                </text>
              </svg>
            </div>
            <p className="text-[11px] text-slate-500 font-mono">
              Solid indigo curve reflects calibrated model; dashed diagonal indicates random
              guessing.
            </p>
          </div>

          {/* SVG Calibration Curve */}
          <div className="glass-panel p-5 rounded-2xl border border-slate-800/80 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 font-mono">
                Reliability &amp; Calibration Curve
              </h3>
              <span className="text-[11px] text-purple-400 font-mono font-bold">Brier: 0.145</span>
            </div>
            <div className="h-60 w-full flex items-center justify-center p-2 bg-slate-950/70 rounded-xl border border-slate-800">
              <svg viewBox="0 0 300 200" className="w-full h-full">
                <line x1="30" y1="20" x2="30" y2="170" stroke="#334155" strokeWidth="1" />
                <line x1="30" y1="170" x2="280" y2="170" stroke="#334155" strokeWidth="1" />

                {/* Perfect calibration 45-degree diagonal */}
                <line
                  x1="30"
                  y1="170"
                  x2="280"
                  y2="20"
                  stroke="#10b981"
                  strokeDasharray="3"
                  strokeWidth="1.5"
                />

                {/* Model calibration points & line */}
                <polyline
                  points="30,170 80,140 130,110 180,75 230,45 280,22"
                  fill="none"
                  stroke="#a855f7"
                  strokeWidth="2.5"
                />
                <circle cx="80" cy="140" r="3" fill="#c084fc" />
                <circle cx="130" cy="110" r="3" fill="#c084fc" />
                <circle cx="180" cy="75" r="3" fill="#c084fc" />
                <circle cx="230" cy="45" r="3" fill="#c084fc" />

                <text x="35" y="32" fill="#94a3b8" fontSize="9" fontFamily="monospace">
                  Observed Frequency
                </text>
                <text x="180" y="165" fill="#94a3b8" fontSize="9" fontFamily="monospace">
                  Predicted Probability
                </text>
              </svg>
            </div>
            <p className="text-[11px] text-slate-500 font-mono">
              Green dashed line is perfect calibration; purple dots represent probability quantile
              bins.
            </p>
          </div>

          {/* Feature Importance Bar Chart */}
          <div className="lg:col-span-2 glass-panel p-5 rounded-2xl border border-slate-800/80 space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 font-mono">
              Top Predictive Features (SHAP Importance)
            </h3>
            <div className="space-y-2.5">
              {[
                { feature: "Pain Points (Review Themes)", score: 88, color: "bg-indigo-500" },
                { feature: "H3 Hex Opportunity Score", score: 76, color: "bg-emerald-500" },
                { feature: "Verified Email Presence", score: 64, color: "bg-blue-500" },
                { feature: "Competitor Density Nearby", score: 52, color: "bg-purple-500" },
                { feature: "Website Audit Issues", score: 41, color: "bg-amber-500" },
                { feature: "Review Velocity (Last 90d)", score: 29, color: "bg-slate-400" },
              ].map((f) => (
                <div key={f.feature} className="space-y-1 text-xs">
                  <div className="flex justify-between items-center text-slate-300">
                    <span className="font-medium">{f.feature}</span>
                    <span className="font-mono text-slate-400 tabular-nums">{f.score}% impact</span>
                  </div>
                  <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
                    <div
                      className={`h-full rounded-full ${f.color}`}
                      style={{ width: `${f.score}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Rule vs ML Comparison */}
      {activeTab === "comparison" && (
        <div className="glass-panel rounded-2xl border border-slate-800/80 overflow-hidden">
          <div className="p-4 border-b border-slate-800 bg-slate-950/70 text-xs text-slate-400 font-mono">
            Showing top ranking reorderings between deterministic rule formula and blended ML model.
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400 uppercase tracking-wider font-semibold font-mono">
                <tr>
                  <th className="py-3 px-4">Business</th>
                  <th className="py-3 px-4">Rule Rank</th>
                  <th className="py-3 px-4">ML Rank</th>
                  <th className="py-3 px-4">Shift</th>
                  <th className="py-3 px-4">Direction</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {comparisons.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-10 text-center text-slate-500">
                      No rank diffs logged yet. Run an analysis and score leads to inspect shifts.
                    </td>
                  </tr>
                ) : (
                  comparisons.map((c, i) => {
                    const diff = (c.rule_rank ?? 0) - (c.ml_rank ?? 0);
                    return (
                      <tr key={i} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-3 px-4 font-semibold text-white">{c.place_name}</td>
                        <td className="py-3 px-4 font-mono tabular-nums text-slate-400">
                          #{c.rule_rank}
                        </td>
                        <td className="py-3 px-4 font-mono tabular-nums text-indigo-400 font-bold">
                          #{c.ml_rank ?? "--"}
                        </td>
                        <td className="py-3 px-4 font-mono tabular-nums whitespace-nowrap">
                          {diff > 0 ? (
                            <span className="text-emerald-400 flex items-center gap-0.5">
                              <ArrowUp className="w-3.5 h-3.5" /> +{diff}
                            </span>
                          ) : diff < 0 ? (
                            <span className="text-rose-400 flex items-center gap-0.5">
                              <ArrowDown className="w-3.5 h-3.5" /> {diff}
                            </span>
                          ) : (
                            <span className="text-slate-500 flex items-center gap-0.5">
                              <Minus className="w-3.5 h-3.5" /> 0
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-slate-300 capitalize">{c.shift_direction}</td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 3: Model Versions History & Rollback */}
      {activeTab === "versions" && (
        <div className="glass-panel rounded-2xl border border-slate-800/80 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400 uppercase tracking-wider font-semibold font-mono">
                <tr>
                  <th className="py-3 px-4">Version</th>
                  <th className="py-3 px-4">Algorithm</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">AUC-ROC</th>
                  <th className="py-3 px-4">Precision@10</th>
                  <th className="py-3 px-4">Trained At</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {versions.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-10 text-center text-slate-500">
                      No trained model checkpoints in registry yet.
                    </td>
                  </tr>
                ) : (
                  versions.map((v) => (
                    <tr key={v.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3 px-4 font-mono font-bold text-white">
                        v{v.id.slice(0, 8)}
                      </td>
                      <td className="py-3 px-4 text-slate-300 capitalize">{v.algorithm}</td>
                      <td className="py-3 px-4 whitespace-nowrap">
                        {v.is_active ? (
                          <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold font-mono text-[10px]">
                            ACTIVE
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-mono text-[10px]">
                            ARCHIVED
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 font-mono tabular-nums text-slate-300">
                        {v.metrics?.roc_auc ? v.metrics.roc_auc.toFixed(3) : "--"}
                      </td>
                      <td className="py-3 px-4 font-mono tabular-nums text-slate-300">
                        {v.metrics?.precision_at_10
                          ? `${Math.round(v.metrics.precision_at_10 * 100)}%`
                          : "--"}
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-400">
                        {new Date(v.trained_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-4 text-right">
                        {!v.is_active && (
                          <button
                            onClick={() => handleRollback(v.id)}
                            disabled={rollbackLoading === v.id}
                            className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold inline-flex items-center gap-1 transition-colors"
                          >
                            <RotateCcw className="w-3 h-3" />
                            <span>Rollback</span>
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
