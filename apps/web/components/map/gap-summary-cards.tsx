"use client";

import React from "react";
import { Sparkles, AlertCircle, ArrowUpRight } from "lucide-react";
import { GapSummaryOut } from "@/lib/types";

interface GapSummaryCardsProps {
  summary: GapSummaryOut | null;
  onSelectHex: (h3Index: string) => void;
}

export function GapSummaryCards({ summary, onSelectHex }: GapSummaryCardsProps) {
  if (!summary) return null;

  return (
    <div
      data-testid="gap-summary-cards"
      className="absolute top-16 left-4 z-20 flex flex-col gap-3 max-w-sm w-full pointer-events-none"
    >
      {/* Top 3 Opportunity Card */}
      <div className="glass-panel bg-white/90 dark:bg-[#0B0F17]/90 border border-emerald-500/30 rounded-2xl p-4 shadow-2xl pointer-events-auto transition-all">
        <div className="flex items-center justify-between mb-2.5">
          <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5 font-mono">
            <Sparkles className="w-3.5 h-3.5" />
            Top 3 Places to Open a {summary.category}
          </h3>
        </div>

        <div className="space-y-1.5">
          {summary.best_hexes.slice(0, 3).map((hex, idx) => (
            <button
              key={hex.h3_index || idx}
              onClick={() => onSelectHex(hex.h3_index)}
              className="w-full text-left p-2 rounded-xl bg-slate-50 hover:bg-slate-100 dark:bg-slate-900/80 dark:hover:bg-slate-850 border border-emerald-500/20 hover:border-emerald-500/40 transition-colors flex items-center justify-between group"
            >
              <div className="truncate pr-2">
                <div className="flex items-center gap-2">
                  <span className="w-4 h-4 rounded-full bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-[10px] font-mono font-bold flex items-center justify-center">
                    {idx + 1}
                  </span>
                  <span className="text-xs font-semibold text-slate-900 dark:text-white font-mono tabular-nums">
                    Score {Math.round(hex.opportunity_score)}/100
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate mt-0.5 pl-6">
                  {hex.reasons?.[0] || "Prime unmet demand"}
                </p>
              </div>
              <ArrowUpRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-emerald-500 dark:text-slate-500 dark:group-hover:text-emerald-400 transition-colors flex-shrink-0" />
            </button>
          ))}
        </div>
      </div>

      {/* Most Saturated Card */}
      <div className="glass-panel bg-white/90 dark:bg-[#0B0F17]/90 border border-rose-500/30 rounded-2xl p-4 shadow-2xl pointer-events-auto transition-all">
        <div className="flex items-center justify-between mb-2.5">
          <h3 className="text-xs font-bold uppercase tracking-wider text-rose-600 dark:text-rose-400 flex items-center gap-1.5 font-mono">
            <AlertCircle className="w-3.5 h-3.5" />
            Most Saturated Areas
          </h3>
        </div>

        <div className="space-y-1.5">
          {summary.saturated_hexes.slice(0, 3).map((hex, idx) => (
            <button
              key={hex.h3_index || idx}
              onClick={() => onSelectHex(hex.h3_index)}
              className="w-full text-left p-2 rounded-xl bg-slate-50 hover:bg-slate-100 dark:bg-slate-900/80 dark:hover:bg-slate-850 border border-rose-500/20 hover:border-rose-500/40 transition-colors flex items-center justify-between group"
            >
              <div className="truncate pr-2">
                <div className="flex items-center gap-2">
                  <span className="w-4 h-4 rounded-full bg-rose-500/20 text-rose-600 dark:text-rose-400 text-[10px] font-mono font-bold flex items-center justify-center">
                    {idx + 1}
                  </span>
                  <span className="text-xs font-semibold text-slate-900 dark:text-white font-mono tabular-nums">
                    Score {Math.round(hex.opportunity_score)}/100
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate mt-0.5 pl-6">
                  {hex.reasons?.[0] || "High competitor density"}
                </p>
              </div>
              <ArrowUpRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-rose-500 dark:text-slate-500 dark:group-hover:text-rose-400 transition-colors flex-shrink-0" />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
