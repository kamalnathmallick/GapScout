/**
 * Color-blind-safe diverging and sequential color palettes for GapScout.
 * Uses Okabe-Ito and Viridis/ColorBrewer inspired scales.
 */

import { HexMetricOut } from "./types";

export type MetricType = "opportunity" | "supply" | "density" | "avg_rating" | "demand_proxy";

export interface LegendItem {
  color: string;
  label: string;
}

export interface LegendConfig {
  title: string;
  items: LegendItem[];
}

export function getMetricColor(
  metric: HexMetricOut,
  activeMetric: MetricType,
  opacity = 0.75,
): [number, number, number, number] {
  const alpha = Math.round(Math.max(0.1, Math.min(1.0, opacity)) * 255);

  switch (activeMetric) {
    case "opportunity": {
      const score = metric.opportunity_score;
      if (score === null || score === undefined || metric.label === "insufficient_data") {
        return [107, 114, 128, Math.round(alpha * 0.5)]; // Neutral gray
      }
      // Diverging palette: Red (oversaturated) -> Amber -> Emerald (underserved)
      if (score >= 80) return [16, 185, 129, alpha]; // Emerald 500
      if (score >= 65) return [20, 184, 166, alpha]; // Teal 500
      if (score >= 45) return [245, 158, 11, alpha]; // Amber 500
      if (score >= 30) return [249, 115, 22, alpha]; // Orange 500
      return [239, 68, 68, alpha]; // Red 500
    }

    case "supply": {
      const supply = metric.supply_count;
      // Inverted: Low supply is dark teal, high supply is hot coral
      if (supply === 0) return [52, 211, 153, alpha]; // Emerald
      if (supply <= 2) return [45, 212, 191, alpha]; // Teal
      if (supply <= 5) return [56, 189, 248, alpha]; // Sky
      if (supply <= 10) return [251, 191, 36, alpha]; // Yellow
      if (supply <= 20) return [248, 113, 113, alpha]; // Rose
      return [225, 29, 72, alpha]; // Red 600
    }

    case "density": {
      const density = metric.density_per_km2 || 0;
      if (density === 0) return [148, 163, 184, Math.round(alpha * 0.4)];
      if (density <= 5) return [96, 165, 250, alpha]; // Blue 400
      if (density <= 15) return [129, 140, 248, alpha]; // Indigo 400
      if (density <= 30) return [168, 85, 247, alpha]; // Purple 500
      return [236, 72, 153, alpha]; // Pink 500
    }

    case "avg_rating": {
      const rating = metric.avg_rating;
      if (rating === null || rating === undefined) {
        return [107, 114, 128, Math.round(alpha * 0.4)];
      }
      if (rating >= 4.4) return [34, 197, 94, alpha]; // Green 500
      if (rating >= 4.0) return [59, 130, 246, alpha]; // Blue 500
      if (rating >= 3.5) return [234, 179, 8, alpha]; // Yellow 500
      if (rating >= 3.0) return [249, 115, 22, alpha]; // Orange 500
      return [239, 68, 68, alpha]; // Red 500
    }

    case "demand_proxy": {
      const demand = metric.demand_proxy || 0;
      if (demand === 0) return [107, 114, 128, Math.round(alpha * 0.4)];
      if (demand <= 20) return [125, 211, 252, alpha];
      if (demand <= 50) return [59, 130, 246, alpha];
      if (demand <= 80) return [99, 102, 241, alpha];
      return [139, 92, 246, alpha]; // Violet 500
    }

    default:
      return [99, 102, 241, alpha];
  }
}

export function getLegendConfig(activeMetric: MetricType): LegendConfig {
  switch (activeMetric) {
    case "opportunity":
      return {
        title: "Opportunity Score",
        items: [
          { color: "rgb(16, 185, 129)", label: "80 - 100 (Prime Gap)" },
          { color: "rgb(20, 184, 166)", label: "65 - 79 (Underserved)" },
          { color: "rgb(245, 158, 11)", label: "45 - 64 (Balanced)" },
          { color: "rgb(249, 115, 22)", label: "30 - 44 (Competitive)" },
          { color: "rgb(239, 68, 68)", label: "0 - 29 (Oversaturated)" },
          { color: "rgb(107, 114, 128)", label: "Insufficient Data" },
        ],
      };

    case "supply":
      return {
        title: "Competitor Count",
        items: [
          { color: "rgb(52, 211, 153)", label: "0 businesses" },
          { color: "rgb(45, 212, 191)", label: "1 - 2 businesses" },
          { color: "rgb(56, 189, 248)", label: "3 - 5 businesses" },
          { color: "rgb(251, 191, 36)", label: "6 - 10 businesses" },
          { color: "rgb(225, 29, 72)", label: "11+ businesses" },
        ],
      };

    case "density":
      return {
        title: "Density (per km²)",
        items: [
          { color: "rgb(96, 165, 250)", label: "< 5 / km²" },
          { color: "rgb(129, 140, 248)", label: "5 - 15 / km²" },
          { color: "rgb(168, 85, 247)", label: "15 - 30 / km²" },
          { color: "rgb(236, 72, 153)", label: "> 30 / km²" },
        ],
      };

    case "avg_rating":
      return {
        title: "Average Customer Rating",
        items: [
          { color: "rgb(34, 197, 94)", label: "≥ 4.4 ★ (High quality)" },
          { color: "rgb(59, 130, 246)", label: "4.0 - 4.3 ★" },
          { color: "rgb(234, 179, 8)", label: "3.5 - 3.9 ★" },
          { color: "rgb(239, 68, 68)", label: "< 3.5 ★ (Quality gap)" },
        ],
      };

    case "demand_proxy":
      return {
        title: "Anchor Demand Proxy",
        items: [
          { color: "rgb(125, 211, 252)", label: "Low anchor volume" },
          { color: "rgb(59, 130, 246)", label: "Moderate anchors" },
          { color: "rgb(99, 102, 241)", label: "High footfall anchors" },
          { color: "rgb(139, 92, 246)", label: "Dense commercial hub" },
        ],
      };
  }
}
