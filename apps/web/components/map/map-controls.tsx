"use client";

import React, { useState } from "react";
import { Layers, Sliders, MapPin, Download, Share2, FileSpreadsheet, Check } from "lucide-react";
import { MetricType, getLegendConfig } from "@/lib/color-scale";

interface MapControlsProps {
  activeMetric: MetricType;
  onMetricChange: (metric: MetricType) => void;
  opacity: number;
  onOpacityChange: (opacity: number) => void;
  showMarkers: boolean;
  onToggleMarkers: () => void;
  onExportPNG: () => void;
  onExportCSV: () => void;
  onShare: () => void;
  isExportingPNG?: boolean;
}

export function MapControls({
  activeMetric,
  onMetricChange,
  opacity,
  onOpacityChange,
  showMarkers,
  onToggleMarkers,
  onExportPNG,
  onExportCSV,
  onShare,
  isExportingPNG,
}: MapControlsProps) {
  const [copied, setCopied] = useState(false);
  const legend = getLegendConfig(activeMetric);

  const handleShareClick = () => {
    onShare();
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const metricOptions: { value: MetricType; label: string }[] = [
    { value: "opportunity", label: "Opportunity Score" },
    { value: "supply", label: "Competitor Count" },
    { value: "density", label: "Supply Density" },
    { value: "avg_rating", label: "Average Rating" },
    { value: "demand_proxy", label: "Anchor Demand" },
  ];

  return (
    <div
      data-testid="map-controls"
      className="absolute bottom-6 left-6 z-20 flex flex-col gap-3 max-w-sm w-full pointer-events-none"
    >
      {/* Legend & Controls Card */}
      <div className="bg-gray-900/95 backdrop-blur-md border border-gray-800 rounded-2xl p-4 shadow-2xl pointer-events-auto text-white space-y-4">
        {/* Metric Selector */}
        <div>
          <label className="text-[11px] font-semibold uppercase tracking-wider text-gray-400 block mb-1.5 flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-indigo-400" />
            <span>Map Metric</span>
          </label>
          <select
            data-testid="metric-select"
            value={activeMetric}
            onChange={(e) => onMetricChange(e.target.value as MetricType)}
            className="w-full px-3 py-1.5 rounded-xl bg-gray-950 border border-gray-800 text-xs text-white focus:outline-none focus:border-indigo-500 font-medium"
          >
            {metricOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Legend */}
        <div>
          <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400 block mb-2">
            Legend: {legend.title}
          </span>
          <div className="grid grid-cols-2 gap-1.5 text-[11px]">
            {legend.items.map((item, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <span
                  className="w-3 h-3 rounded-md flex-shrink-0 border border-black/30"
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-gray-300 truncate">{item.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Sliders and Toggles */}
        <div className="pt-2 border-t border-gray-800 space-y-3">
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-400 flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-gray-500" />
              Hex Opacity: {Math.round(opacity * 100)}%
            </span>
            <input
              type="range"
              min="0.2"
              max="1.0"
              step="0.05"
              value={opacity}
              onChange={(e) => onOpacityChange(parseFloat(e.target.value))}
              className="w-24 accent-indigo-500 cursor-pointer"
            />
          </div>

          <label className="flex items-center justify-between text-xs cursor-pointer select-none">
            <span className="text-gray-400 flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5 text-gray-500" />
              Show Business Markers
            </span>
            <input
              type="checkbox"
              checked={showMarkers}
              onChange={onToggleMarkers}
              className="w-4 h-4 rounded accent-indigo-500 cursor-pointer"
            />
          </label>
        </div>

        {/* Export Bar */}
        <div className="pt-2 border-t border-gray-800 flex items-center gap-2">
          <button
            onClick={onExportPNG}
            disabled={isExportingPNG}
            className="flex-1 inline-flex items-center justify-center gap-1.5 py-1.5 px-2.5 rounded-lg bg-gray-950 hover:bg-gray-800 border border-gray-800 text-xs text-gray-300 hover:text-white transition-colors"
            title="Download PNG snapshot of map"
          >
            <Download className="w-3.5 h-3.5" />
            <span>PNG</span>
          </button>

          <button
            onClick={onExportCSV}
            className="flex-1 inline-flex items-center justify-center gap-1.5 py-1.5 px-2.5 rounded-lg bg-gray-950 hover:bg-gray-800 border border-gray-800 text-xs text-gray-300 hover:text-white transition-colors"
            title="Download hex metrics as CSV"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>CSV</span>
          </button>

          <button
            onClick={handleShareClick}
            className="flex-1 inline-flex items-center justify-center gap-1.5 py-1.5 px-2.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-xs text-indigo-300 hover:text-white transition-colors"
            title="Copy share link"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-emerald-400">Copied!</span>
              </>
            ) : (
              <>
                <Share2 className="w-3.5 h-3.5" />
                <span>Share</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
