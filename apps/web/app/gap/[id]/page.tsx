"use client";

import React, { useState, useRef } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Loader2, Layers, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { HexMetricOut, HexMetricsResponse, GapSummaryOut, PlacesListOut } from "@/lib/types";
import { MetricType } from "@/lib/color-scale";
import { useTheme } from "@/components/theme-provider";
import { GapMap, GapMapRef } from "@/components/map/gap-map";
import { HexDrawer } from "@/components/map/hex-drawer";
import { MapControls } from "@/components/map/map-controls";
import { GapSummaryCards } from "@/components/map/gap-summary-cards";

export default function GapMapPage() {
  const params = useParams();
  const jobId = (params?.id as string) || "";
  const mapRef = useRef<GapMapRef>(null);
  const { theme } = useTheme();

  const [activeMetric, setActiveMetric] = useState<MetricType>("opportunity");
  const [opacity, setOpacity] = useState(0.75);
  const [showMarkers, setShowMarkers] = useState(false);
  const [selectedHex, setSelectedHex] = useState<HexMetricOut | null>(null);
  const [isExportingPNG, setIsExportingPNG] = useState(false);
  const [resolution, setResolution] = useState<number>(8);
  const [userBasemapStyle, setUserBasemapStyle] = useState<string | null>(null);

  // Default basemap depends on the current theme (Positron for light, Dark for dark)
  const defaultBasemapStyle =
    theme === "light"
      ? "https://tiles.openfreemap.org/styles/positron"
      : "https://tiles.openfreemap.org/styles/dark";
  const basemapStyle = userBasemapStyle ?? defaultBasemapStyle;

  const isClient = typeof window !== "undefined";

  // 1. Fetch hex metrics (client-side only)
  const {
    data: hexData,
    isLoading: isLoadingHexes,
    isError: isHexError,
    error: hexError,
  } = useQuery<HexMetricsResponse>({
    queryKey: ["gap-hexes", jobId],
    queryFn: () => api.getGapHexes(jobId),
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

  // Progressive Zoom & Resolution Change
  const handleResolutionChange = (newRes: number) => {
    setResolution(newRes);
    if (newRes === 9) {
      mapRef.current?.setZoomLevel(15.2);
    } else if (newRes === 7) {
      mapRef.current?.setZoomLevel(11.5);
    } else {
      mapRef.current?.setZoomLevel(13);
    }
  };

  // Export PNG snapshot
  const handleExportPNG = () => {
    setIsExportingPNG(true);
    try {
      const dataUrl = mapRef.current?.getCanvasDataURL();
      if (!dataUrl) {
        alert("Unable to capture map screenshot.");
        setIsExportingPNG(false);
        return;
      }
      const link = document.createElement("a");
      link.download = `gapscout-${jobId}-map.png`;
      link.href = dataUrl;
      link.click();
    } catch {
      alert("PNG export failed.");
    } finally {
      setIsExportingPNG(false);
    }
  };

  // Export CSV
  const handleExportCSV = () => {
    if (hexes.length === 0) return;
    const headers = [
      "h3_index",
      "resolution",
      "opportunity_score",
      "label",
      "supply_count",
      "density_per_km2",
      "avg_rating",
      "demand_proxy",
    ];
    const rows = hexes.map((h) => [
      h.h3_index,
      h.resolution,
      h.opportunity_score,
      h.label,
      h.supply_count,
      h.density_per_km2,
      h.avg_rating,
      h.demand_proxy,
    ]);
    const csvContent =
      "data:text/csv;charset=utf-8," +
      [headers.join(","), ...rows.map((e) => e.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `gapscout-hexes-${hexData?.category || "analysis"}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Share
  const handleShare = () => {
    if (typeof window !== "undefined") {
      navigator.clipboard.writeText(window.location.href);
    }
  };

  return (
    <div className="relative w-full h-[calc(100vh-3.5rem)] overflow-hidden bg-slate-100 dark:bg-[#0B0F17] flex flex-col">
      {/* Top Banner & Mini-Nav */}
      <div className="absolute top-4 left-4 z-20 flex items-center gap-3 pointer-events-auto">
        <div className="glass-panel bg-white/90 dark:bg-[#0B0F17]/90 px-3.5 py-1.5 rounded-xl border border-slate-200/90 dark:border-[#1F2937] text-xs shadow-lg flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="font-bold text-slate-900 dark:text-white font-mono">
              Market Gap Intelligence
            </span>
          </div>
          <span className="text-slate-300 dark:text-slate-700">|</span>
          <span className="font-semibold text-indigo-600 dark:text-indigo-400 capitalize">
            {hexData?.category || "Local"} Market Gap
          </span>
          <span className="px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-[11px] font-mono text-slate-700 dark:text-slate-300">
            {hexes.length} Hexes
          </span>
        </div>
      </div>

      <div className="absolute top-4 right-4 z-20 flex items-center gap-2 pointer-events-auto">
        <Link
          href={`/jobs/${jobId}`}
          className="glass-panel bg-white/90 dark:bg-[#0B0F17]/90 border border-slate-200/90 dark:border-[#1F2937] px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors flex items-center gap-1.5 shadow-lg"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Job Details</span>
        </Link>
        <Link
          href="/leads"
          className="glass-panel px-3 py-1.5 rounded-xl text-xs font-semibold bg-indigo-600/10 dark:bg-indigo-600/30 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-600/20 dark:hover:bg-indigo-600/40 border border-indigo-500/30 transition-colors flex items-center gap-1.5 shadow-lg"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>View Leads</span>
        </Link>
      </div>

      {/* Loading state */}
      {isLoadingHexes && (
        <div className="absolute inset-0 z-30 flex items-center justify-center bg-slate-900/40 dark:bg-slate-950/70 backdrop-blur-sm">
          <div className="glass-panel bg-white/95 dark:bg-[#0B0F17]/95 border border-slate-200 dark:border-[#1F2937] p-6 rounded-2xl flex flex-col items-center gap-3 text-slate-700 dark:text-slate-300 text-xs font-mono shadow-2xl">
            <Loader2 className="w-7 h-7 animate-spin text-indigo-500 dark:text-indigo-400" />
            <span>Rendering H3 hexagonal gap map...</span>
          </div>
        </div>
      )}

      {/* Error state */}
      {isHexError && (
        <div className="absolute inset-0 z-30 flex items-center justify-center bg-slate-900/50 dark:bg-slate-950/80">
          <div className="glass-panel bg-white/95 dark:bg-[#0B0F17]/95 border border-slate-200 dark:border-[#1F2937] p-6 rounded-2xl max-w-md text-center space-y-3 shadow-2xl">
            <Layers className="w-8 h-8 text-rose-500 dark:text-rose-400 mx-auto" />
            <p className="text-sm font-semibold text-slate-900 dark:text-white">
              Could not load gap analysis
            </p>
            <p className="text-xs text-rose-600 dark:text-rose-300">
              {hexError instanceof Error ? hexError.message : "Data unavailable"}
            </p>
            <Link
              href={`/jobs/${jobId}`}
              className="inline-block px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition-colors shadow-sm"
            >
              Back to Job Detail
            </Link>
          </div>
        </div>
      )}

      {/* Map Canvas */}
      <div className="flex-1 w-full h-full relative">
        <GapMap
          ref={mapRef}
          hexes={hexes}
          places={places}
          activeMetric={activeMetric}
          opacity={opacity}
          showMarkers={showMarkers}
          selectedHex={selectedHex}
          onSelectHex={handleSelectHex}
          basemapStyle={basemapStyle}
          resolution={resolution}
          onResolutionChange={handleResolutionChange}
        />

        {/* Floating Top 3 / Saturated Cards */}
        {summaryData && (
          <GapSummaryCards summary={summaryData} onSelectHex={handleSelectHexByIndex} />
        )}

        {/* Floating Bottom Left Controls */}
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
          basemapStyle={basemapStyle}
          onBasemapStyleChange={setUserBasemapStyle}
          resolution={resolution}
          onResolutionChange={handleResolutionChange}
        />

        {/* Slide-over Right Hex Drawer */}
        {selectedHex && <HexDrawer hex={selectedHex} onClose={() => setSelectedHex(null)} />}
      </div>
    </div>
  );
}
