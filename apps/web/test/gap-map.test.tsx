import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { getMetricColor, getLegendConfig } from "@/lib/color-scale";
import { HexDrawer } from "@/components/map/hex-drawer";
import { GapSummaryCards } from "@/components/map/gap-summary-cards";
import { MapControls } from "@/components/map/map-controls";
import { HexMetricOut, GapSummaryOut } from "@/lib/types";
import { api } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: {
    listPlaces: vi.fn(),
  },
}));

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const mockHex: HexMetricOut = {
  id: "hex-1",
  search_job_id: "job-1",
  category: "cafe",
  h3_index: "88618925d3fffff",
  resolution: 8,
  supply_count: 2,
  density_per_km2: 2.5,
  avg_rating: 4.5,
  avg_review_count: 120,
  demand_proxy: 75,
  opportunity_score: 82.5,
  label: "underserved",
  explanation: {
    top_reasons: ["0 competitors within 1 km", "14 offices nearby"],
    metrics: {},
  },
  computed_at: new Date().toISOString(),
};

const mockSummary: GapSummaryOut = {
  job_id: "job-1",
  category: "cafe",
  resolution: 8,
  total_hexes: 10,
  underserved_count: 3,
  balanced_count: 5,
  oversaturated_count: 2,
  insufficient_data_count: 0,
  area_median_rating: 4.1,
  best_hexes: [
    {
      h3_index: "88618925d3fffff",
      opportunity_score: 88,
      label: "underserved",
      reasons: ["High office demand", "0 competitors within 1 km"],
    },
  ],
  saturated_hexes: [
    {
      h3_index: "88618925d1fffff",
      opportunity_score: 22,
      label: "oversaturated",
      reasons: ["12 cafes within 500m"],
    },
  ],
};

describe("Gap Map Color Scale & Legends", () => {
  it("computes diverging colors for opportunity scores", () => {
    // High opportunity -> emerald (16, 185, 129)
    const primeColor = getMetricColor(mockHex, "opportunity", 1.0);
    expect(primeColor[0]).toBe(16);
    expect(primeColor[1]).toBe(185);
    expect(primeColor[2]).toBe(129);

    // Oversaturated -> red (239, 68, 68)
    const saturatedHex = { ...mockHex, opportunity_score: 15, label: "oversaturated" as const };
    const saturatedColor = getMetricColor(saturatedHex, "opportunity", 1.0);
    expect(saturatedColor[0]).toBe(239);
    expect(saturatedColor[1]).toBe(68);
    expect(saturatedColor[2]).toBe(68);

    // Insufficient data -> neutral gray
    const insufficientHex = { ...mockHex, label: "insufficient_data" as const };
    const grayColor = getMetricColor(insufficientHex, "opportunity", 1.0);
    expect(grayColor[0]).toBe(107);
    expect(grayColor[1]).toBe(114);
  });

  it("returns configured legend items for each metric", () => {
    const oppLegend = getLegendConfig("opportunity");
    expect(oppLegend.title).toBe("Opportunity Score");
    expect(oppLegend.items.length).toBeGreaterThanOrEqual(4);

    const supplyLegend = getLegendConfig("supply");
    expect(supplyLegend.title).toBe("Competitor Count");
  });
});

describe("HexDrawer Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listPlaces).mockResolvedValue({
      items: [],
      pagination: { total: 0, limit: 50, offset: 0, has_more: false },
    });
  });

  it("renders selected hex metrics and explanation reasons", async () => {
    vi.mocked(api.listPlaces).mockResolvedValueOnce({
      items: [
        {
          id: "p1",
          workspace_id: "ws1",
          name: "Blue Tokai Coffee",
          category: "cafe",
          normalized_category: "cafe",
          address: "100ft Road, Indiranagar",
          phone_e164: "+919876543210",
          website: "https://bluetokai.com",
          website_domain: "bluetokai.com",
          email: "info@bluetokai.com",
          rating: 4.6,
          review_count: 350,
          price_level: 2,
          h3_r8: "88618925d3fffff",
          is_closed: false,
          latitude: 12.97,
          longitude: 77.64,
          first_seen_at: new Date().toISOString(),
          last_seen_at: new Date().toISOString(),
        },
      ],
      pagination: { total: 1, limit: 50, offset: 0, has_more: false },
    });

    const onClose = vi.fn();
    renderWithClient(<HexDrawer hex={mockHex} onClose={onClose} />);

    expect(screen.getByTestId("hex-drawer")).toBeInTheDocument();
    expect(screen.getByText(/Prime Opportunity/i)).toBeInTheDocument();
    expect(screen.getByText("0 competitors within 1 km")).toBeInTheDocument();
    expect(screen.getByText("14 offices nearby")).toBeInTheDocument();
    expect(screen.getByText("2 businesses")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Blue Tokai Coffee")).toBeInTheDocument();
      expect(screen.getByText("100ft Road, Indiranagar")).toBeInTheDocument();
    });
  });

  it("calls onClose when close button is clicked", () => {
    const onClose = vi.fn();
    renderWithClient(<HexDrawer hex={mockHex} onClose={onClose} />);

    const closeBtn = screen.getByTitle("Close details");
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalled();
  });
});

describe("GapSummaryCards Component", () => {
  it("renders top 3 and saturated cards and handles hex selection", () => {
    const onSelectHex = vi.fn();
    render(<GapSummaryCards summary={mockSummary} onSelectHex={onSelectHex} />);

    expect(screen.getByTestId("gap-summary-cards")).toBeInTheDocument();
    expect(screen.getByText(/Top 3 Places to Open a cafe/i)).toBeInTheDocument();
    expect(screen.getByText(/Most Saturated Areas/i)).toBeInTheDocument();
    expect(screen.getByText("Score 88/100")).toBeInTheDocument();
    expect(screen.getByText("Score 22/100")).toBeInTheDocument();

    // Click top best hex
    const bestHexBtn = screen.getByText("Score 88/100").closest("button")!;
    fireEvent.click(bestHexBtn);
    expect(onSelectHex).toHaveBeenCalledWith("88618925d3fffff");
  });
});

describe("MapControls Component", () => {
  it("allows switching metric, toggling markers, and triggering exports", () => {
    const onMetricChange = vi.fn();
    const onOpacityChange = vi.fn();
    const onToggleMarkers = vi.fn();
    const onExportPNG = vi.fn();
    const onExportCSV = vi.fn();
    const onShare = vi.fn();

    render(
      <MapControls
        activeMetric="opportunity"
        onMetricChange={onMetricChange}
        opacity={0.75}
        onOpacityChange={onOpacityChange}
        showMarkers={false}
        onToggleMarkers={onToggleMarkers}
        onExportPNG={onExportPNG}
        onExportCSV={onExportCSV}
        onShare={onShare}
      />,
    );

    expect(screen.getByTestId("map-controls")).toBeInTheDocument();

    // Metric change
    const select = screen.getByTestId("metric-select");
    fireEvent.change(select, { target: { value: "supply" } });
    expect(onMetricChange).toHaveBeenCalledWith("supply");

    // Toggle markers
    const markerToggle = screen.getByRole("checkbox");
    fireEvent.click(markerToggle);
    expect(onToggleMarkers).toHaveBeenCalled();

    // Export buttons
    fireEvent.click(screen.getByText("PNG"));
    expect(onExportPNG).toHaveBeenCalled();

    fireEvent.click(screen.getByText("CSV"));
    expect(onExportCSV).toHaveBeenCalled();

    fireEvent.click(screen.getByText("Share"));
    expect(onShare).toHaveBeenCalled();
  });
});
