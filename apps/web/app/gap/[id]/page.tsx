"use client";

import React, { useState, useRef } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Compass, ArrowLeft, Loader2, Layers, Sparkles, Info } from "lucide-react";
import { api } from "@/lib/api";
import { HexMetricOut, HexMetricsResponse, GapSummaryOut, PlacesListOut } from "@/lib/types";
import { MetricType } from "@/lib/color-scale";
import { GapMap, GapMapRef } from "@/components/map/gap-map";
import { HexDrawer } from "@/components/map/hex-drawer";
import { MapControls } from "@/components/map/map-controls";
import { GapSummaryCards } from "@/components/map/gap-summary-cards";

export default function GapMapPage() {
  const params = useParams();
  const jobId = (params?.id as string) || "";
  const mapRef = useRef<GapMapRef>(null);

  const [activeMetric, setActiveMetric] = useState<MetricType>("opportunity");
  const [opacity, setOpacity] = useState(0.75);
  const [showMarkers, setShowMarkers] = useState(false);
  const [selectedHex, setSelectedHex] = useState<HexMetricOut | null>(null);
  const [isExportingPNG, setIsExportingPNG] = useState(false);

  const isClient = typeof window !== "undefined";

  // 1. Fetch hex metrics (client-side only)
  const {
    data: hexData,
    isLoading: isLoadingHexes,
    isError: isHexError,
    error: hexError,
  } = useQuery<HexMetricsResponse>({
    queryKey: ["gap-hexes", jobId],
    queryFn: () => {
      console.log("EXEC QUERY FN FOR GAP HEXES", jobId);
      return api.getGapHexes(jobId);
    },
    enabled: isClient && !!jobId,
  });

  // 2. Fetch gap summary
  const { data: summaryData } = useQuery<GapSummaryOut>({
    queryKey: ["gap-summary", jobId],
    queryFn: () => api.getGapSummary(jobId),
    enabled: isClient && !!jobId,
  });

  // 3. Fetch places for markers (when enabled)
  const { data: placesData } = useQuery<PlacesListOut>({
    queryKey: ["places-for-map", jobId],
    queryFn: () => api.listPlaces({ limit: 500 }),
    enabled: isClient && showMarkers,
  });

  const hexes = hexData?.hexes || [];
  const places = placesData?.items || [];

  const handleSelectHex = (hex: HexMetricOut) => {
    setSelectedHex(hex);
    mapRef.current?.flyToHex(hex.h3_index);
  };

  const handleSelectHexByIndex = (h3Index: string) => {
    const match = hexes.find((h) => h.h3_index === h3Index);
    if (match) {
      setSelectedHex(match);
    } else {
      setSelectedHex({
        id: h3Index,
        search_job_id: jobId,
        category: hexData?.category || "general",
        h3_index: h3Index,
        resolution: 8,
        supply_count: 0,
        density_per_km2: 0,
        avg_rating: null,
        avg_review_count: 0,
        demand_proxy: 50,
        opportunity_score: 85,
        label: "underserved",
        explanation: {
          top_reasons: ["High demand location"],
          metrics: {},
        },
        computed_at: new Date().toISOString(),
      });
    }
    mapRef.current?.flyToHex(h3Index);
  };

  // Export PNG snapshot
  const handleExportPNG = () => {
    setIsExportingPNG(true);
    try {
      const dataUrl = mapRef.current?.getCanvasDataURL();
      if (!dataUrl) {
        alert("Unable to capture map screenshot.");
        return;
      }
      const a = document.createElement("a");
      a.href = dataUrl;
      a.download = `gapscout-map-${hexData?.category || "analysis"}-${jobId.slice(0, 8)}.png`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } finally {
      setIsExportingPNG(false);
    }
  };

  // Export CSV
  const handleExportCSV = () => {
    if (hexes.length === 0) return;

    const headers = [
      "h3_index",
      "opportunity_score",
      "label",
      "supply_count",
      "density_per_km2",
      "avg_rating",
      "avg_review_count",
      "demand_proxy",
      "top_reasons",
    ];

    const rows = hexes.map((h) => [
      h.h3_index,
      h.opportunity_score ?? "",
      h.label ?? "",
      h.supply_count,
      h.density_per_km2 ?? "",
      h.avg_rating ?? "",
      h.avg_review_count ?? "",
      h.demand_proxy ?? "",
      `"${(h.explanation?.top_reasons || []).join(" | ").replace(/"/g, '""')}"`,
    ]);

    const csvContent = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `gapscout-hexes-${hexData?.category || "analysis"}-${jobId.slice(0, 8)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Share link
  const handleShare = () => {
    if (typeof window !== "undefined") {
      navigator.clipboard.writeText(window.location.href);
    }
  };

  if (isLoadingHexes) {
    return (
      <div className="min-h-screen bg-gray-950 text-white flex flex-col items-center justify-center p-6">
        <Loader2 className="w-10 h-10 animate-spin text-indigo-400 mb-3" />
        <p className="text-sm text-gray-400">Loading hexagonal gap map...</p>
      </div>
    );
  }

  if (isHexError || hexes.length === 0) {
    return (
      <div className="min-h-screen bg-gray-950 text-white p-6 sm:p-10 flex flex-col items-center justify-center text-center">
        <div className="max-w-md p-8 rounded-2xl bg-gray-900 border border-gray-800 space-y-4">
          <div className="w-12 h-12 rounded-xl bg-amber-500/10 text-amber-400 mx-auto flex items-center justify-center">
            <Info className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-bold text-white">Gap analysis not ready</h2>
          <p className="text-xs text-gray-400">
            {hexError instanceof Error
              ? hexError.message
              : "No hex opportunity metrics found for this job yet. Check job progress."}
          </p>
          <div className="pt-2 flex justify-center gap-3">
            <Link
              href={`/jobs/${jobId}`}
              className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-medium text-white transition-colors"
            >
              View Job Progress
            </Link>
            <Link
              href="/dashboard"
              className="px-4 py-2 rounded-xl bg-gray-800 hover:bg-gray-700 text-xs font-medium text-gray-300 transition-colors"
            >
              Back to Dashboard
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-[calc(100vh-4rem)] w-full overflow-hidden bg-gray-950 flex flex-col">
      {/* Top Banner Navigation */}
      <div className="h-14 border-b border-gray-800 bg-gray-950/80 backdrop-blur-md px-6 flex items-center justify-between z-20 flex-shrink-0">
        <div className="flex items-center gap-4">
          <Link
            href="/dashboard"
            className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
            title="Back to dashboard"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div className="flex items-center gap-2">
            <Compass className="w-5 h-5 text-indigo-400" />
            <span className="font-bold text-white capitalize text-sm">
              {hexData?.category} Market Gap
            </span>
          </div>
          <span className="hidden sm:inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Layers className="w-3 h-3" />
            {hexes.length} Hexes (Res {hexData?.resolution || 8})
          </span>
          {summaryData && summaryData.underserved_count > 0 && (
            <span className="hidden md:inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Sparkles className="w-3 h-3" />
              {summaryData.underserved_count} Prime Gaps
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          <Link
            href={`/jobs/${jobId}`}
            className="text-xs text-gray-400 hover:text-white transition-colors"
          >
            Job Info
          </Link>
        </div>
      </div>

      {/* Main Map Canvas Area */}
      <div className="relative flex-1 w-full h-full">
        <GapMap
          ref={mapRef}
          hexes={hexes}
          places={places}
          activeMetric={activeMetric}
          opacity={opacity}
          showMarkers={showMarkers}
          selectedHex={selectedHex}
          onSelectHex={handleSelectHex}
        />

        {/* Floating Top Left: Top 3 & Saturated Cards */}
        <GapSummaryCards summary={summaryData || null} onSelectHex={handleSelectHexByIndex} />

        {/* Floating Bottom Left: Controls, Metric Switch & Legend */}
        <MapControls
          activeMetric={activeMetric}
          onMetricChange={setActiveMetric}
          opacity={opacity}
          onOpacityChange={setOpacity}
          showMarkers={showMarkers}
          onToggleMarkers={() => setShowMarkers(!showMarkers)}
          onExportPNG={handleExportPNG}
          onExportCSV={handleExportCSV}
          onShare={handleShare}
          isExportingPNG={isExportingPNG}
        />

        {/* Floating Right: Hex Detail Drawer */}
        <HexDrawer hex={selectedHex} onClose={() => setSelectedHex(null)} />
      </div>
    </div>
  );
}
