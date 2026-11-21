"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import {
  X,
  MapPin,
  TrendingUp,
  Star,
  Globe,
  Phone,
  Building2,
  Layers,
  Sparkles,
  ExternalLink,
} from "lucide-react";
import { api } from "@/lib/api";
import { HexMetricOut, PlaceOut, PlacesListOut } from "@/lib/types";

interface HexDrawerProps {
  hex: HexMetricOut | null;
  onClose: () => void;
}

export function HexDrawer({ hex, onClose }: HexDrawerProps) {
  const { data: placesData, isLoading: isLoadingPlaces } = useQuery<PlacesListOut>({
    queryKey: ["places-in-hex", hex?.h3_index],
    queryFn: () =>
      hex
        ? api.listPlaces({ hex: hex.h3_index })
        : Promise.resolve({
            items: [],
            pagination: { total: 0, limit: 50, offset: 0, has_more: false },
          }),
    enabled: !!hex,
  });

  if (!hex) return null;

  const getScoreBadge = (score: number | null, label: string | null) => {
    const s = score ?? 0;
    if (label === "underserved" || s >= 70) {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
          <Sparkles className="w-3.5 h-3.5" />
          Prime Opportunity ({Math.round(s)}/100)
        </span>
      );
    }
    if (label === "balanced" || s >= 45) {
      return (
        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 font-mono">
          Balanced ({Math.round(s)}/100)
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20 font-mono">
        Oversaturated ({Math.round(s)}/100)
      </span>
    );
  };

  const reasons = hex.explanation?.top_reasons || [];
  const places = placesData?.items || [];

  return (
    <aside
      data-testid="hex-drawer"
      className="absolute top-4 right-4 bottom-4 w-96 max-w-[calc(100vw-2rem)] glass-panel bg-slate-950/95 border border-slate-800 rounded-2xl shadow-2xl z-30 flex flex-col overflow-hidden text-white animate-in slide-in-from-right duration-300"
    >
      {/* Header */}
      <div className="p-5 border-b border-slate-800 flex items-start justify-between bg-slate-950/60">
        <div>
          <div className="flex items-center gap-2 mb-1.5 font-mono text-xs">
            <Layers className="w-3.5 h-3.5 text-indigo-400" />
            <span className="text-slate-400">H3 Res {hex.resolution}</span>
            <span className="text-slate-500 truncate max-w-[150px]">{hex.h3_index}</span>
          </div>
          <div>{getScoreBadge(hex.opportunity_score, hex.label)}</div>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          title="Close details"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Scrollable Body */}
      <div className="flex-1 overflow-y-auto p-5 space-y-6">
        {/* Reasons */}
        <div className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 font-mono">
            <TrendingUp className="w-3.5 h-3.5 text-indigo-400" />
            <span>Opportunity Reasons</span>
          </h3>
          {reasons.length > 0 ? (
            <ul className="space-y-1.5">
              {reasons.map((r, i) => (
                <li
                  key={i}
                  className="text-xs text-slate-300 bg-slate-900/80 p-2.5 rounded-xl border border-slate-800/80 flex items-start gap-2"
                >
                  <span className="text-indigo-400 font-bold">•</span>
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-slate-500">No detailed reasons recorded for this cell.</p>
          )}
        </div>

        {/* Metrics Grid */}
        <div className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 font-mono">
            <Building2 className="w-3.5 h-3.5 text-indigo-400" />
            <span>Hex Metrics</span>
          </h3>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-800/80">
              <span className="text-slate-500 block mb-0.5 text-[11px]">Competitor Supply</span>
              <span className="text-base font-bold font-mono text-white tabular-nums">
                {hex.supply_count} businesses
              </span>
            </div>

            <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-800/80">
              <span className="text-slate-500 block mb-0.5 text-[11px]">Supply Density</span>
              <span className="text-base font-bold font-mono text-white tabular-nums">
                {hex.density_per_km2 ? hex.density_per_km2.toFixed(1) : "0"} / km²
              </span>
            </div>

            <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-800/80">
              <span className="text-slate-500 block mb-0.5 text-[11px]">Average Rating</span>
              <span className="text-base font-bold font-mono text-white flex items-center gap-1 tabular-nums">
                <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
                {hex.avg_rating ? hex.avg_rating.toFixed(1) : "N/A"}
                <span className="text-xs text-slate-500 font-normal">
                  ({hex.avg_review_count || 0} rev)
                </span>
              </span>
            </div>

            <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-800/80">
              <span className="text-slate-500 block mb-0.5 text-[11px]">Demand Proxy</span>
              <span className="text-base font-bold font-mono text-indigo-400 tabular-nums">
                {hex.demand_proxy ? Math.round(hex.demand_proxy) : "0"}
              </span>
            </div>
          </div>
        </div>

        {/* Businesses inside hex */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 font-mono">
              <MapPin className="w-3.5 h-3.5 text-indigo-400" />
              <span>Businesses in Hex ({places.length})</span>
            </h3>
          </div>

          {isLoadingPlaces ? (
            <div className="space-y-2">
              {[1, 2].map((n) => (
                <div
                  key={n}
                  className="h-16 rounded-xl bg-slate-900/40 border border-slate-800 animate-pulse"
                />
              ))}
            </div>
          ) : places.length === 0 ? (
            <div className="text-center py-6 px-4 bg-slate-900/40 rounded-xl border border-slate-800 text-xs text-slate-400">
              <p className="font-semibold text-emerald-400 mb-1">Zero Direct Competitors</p>
              <p className="text-slate-500">
                This cell is currently unserved by existing businesses in this category.
              </p>
            </div>
          ) : (
            <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
              {places.map((place: PlaceOut) => (
                <div
                  key={place.id}
                  className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-slate-700 transition-colors text-xs space-y-1.5"
                >
                  <div className="flex justify-between items-start">
                    <span className="font-semibold text-white truncate max-w-[200px]">
                      {place.name}
                    </span>
                    {place.rating !== null && (
                      <span className="inline-flex items-center gap-1 font-mono text-amber-400 font-medium tabular-nums">
                        <Star className="w-3 h-3 fill-amber-400" />
                        {place.rating.toFixed(1)}
                      </span>
                    )}
                  </div>

                  {place.address && (
                    <p className="text-[11px] text-slate-400 truncate">{place.address}</p>
                  )}

                  <div className="flex items-center gap-3 pt-1 text-[11px] text-slate-500">
                    {place.phone_e164 && (
                      <span className="flex items-center gap-1 text-slate-400 font-mono">
                        <Phone className="w-3 h-3" />
                        {place.phone_e164}
                      </span>
                    )}

                    {place.website && (
                      <a
                        href={place.website}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-1 text-indigo-400 hover:underline"
                      >
                        <Globe className="w-3 h-3" />
                        <span>Website</span>
                        <ExternalLink className="w-2.5 h-2.5" />
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
