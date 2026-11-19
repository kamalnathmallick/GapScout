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
      className="absolute top-4 left-4 z-20 flex flex-col gap-3 max-w-sm w-full pointer-events-none"
    >
      {/* Top 3 Opportunity Card */}
      <div className="bg-gray-900/90 backdrop-blur-md border border-emerald-500/30 rounded-2xl p-4 shadow-xl pointer-events-auto transition-all">
        <div className="flex items-center justify-between mb-2.5">
          <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
            <Sparkles className="w-4 h-4" />
            Top 3 Places to Open a {summary.category}
          </h3>
        </div>

        <div className="space-y-1.5">
          {summary.best_hexes.slice(0, 3).map((hex, idx) => (
            <button
              key={hex.h3_index || idx}
              onClick={() => onSelectHex(hex.h3_index)}
              className="w-full text-left p-2 rounded-xl bg-gray-950/70 hover:bg-gray-800 border border-emerald-500/20 hover:border-emerald-500/40 transition-colors flex items-center justify-between group"
            >
              <div className="truncate pr-2">
                <div className="flex items-center gap-2">
                  <span className="w-4 h-4 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px] font-bold flex items-center justify-center">
                    {idx + 1}
                  </span>
                  <span className="text-xs font-semibold text-white">
                    Score {Math.round(hex.opportunity_score)}/100
                  </span>
                </div>
                <p className="text-[11px] text-gray-400 truncate mt-0.5 pl-6">
                  {hex.reasons?.[0] || "Prime unmet demand"}
                </p>
              </div>
              <ArrowUpRight className="w-3.5 h-3.5 text-gray-500 group-hover:text-emerald-400 transition-colors flex-shrink-0" />
            </button>
          ))}
        </div>
      </div>

      {/* Most Saturated Card */}
      <div className="bg-gray-900/90 backdrop-blur-md border border-red-500/20 rounded-2xl p-4 shadow-xl pointer-events-auto transition-all">
        <div className="flex items-center justify-between mb-2.5">
          <h3 className="text-xs font-bold uppercase tracking-wider text-red-400 flex items-center gap-1.5">
            <AlertCircle className="w-4 h-4" />
            Most Saturated Areas
          </h3>
        </div>

        <div className="space-y-1.5">
          {summary.saturated_hexes.slice(0, 3).map((hex, idx) => (
            <button
              key={hex.h3_index || idx}
              onClick={() => onSelectHex(hex.h3_index)}
              className="w-full text-left p-2 rounded-xl bg-gray-950/70 hover:bg-gray-800 border border-red-500/20 hover:border-red-500/40 transition-colors flex items-center justify-between group"
            >
              <div className="truncate pr-2">
                <div className="flex items-center gap-2">
                  <span className="w-4 h-4 rounded-full bg-red-500/20 text-red-400 text-[10px] font-bold flex items-center justify-center">
                    {idx + 1}
                  </span>
                  <span className="text-xs font-semibold text-white">
                    Score {Math.round(hex.opportunity_score)}/100
                  </span>
                </div>
                <p className="text-[11px] text-gray-400 truncate mt-0.5 pl-6">
                  {hex.reasons?.[0] || "High competitor density"}
                </p>
              </div>
              <ArrowUpRight className="w-3.5 h-3.5 text-gray-500 group-hover:text-red-400 transition-colors flex-shrink-0" />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
