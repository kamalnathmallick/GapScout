import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import JobDetailPage from "@/app/jobs/[id]/page";
import { api } from "@/lib/api";

const mockParams = { id: "job-abc" };

vi.mock("next/navigation", () => ({
  useParams: () => mockParams,
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  api: {
    getJob: vi.fn(),
    cancelJob: vi.fn(),
    resumeJob: vi.fn(),
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

describe("JobDetailPage Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders running progress state with metrics", async () => {
    mockParams.id = "job-abc";
    vi.mocked(api.getJob).mockResolvedValueOnce({
      job_id: "job-abc",
      status: "running",
      cells_total: 10,
      cells_done: 4,
      pct_complete: 40,
      places_found: 32,
      errors_count: 0,
      quality_report: null,
      gap_summary: null,
    });

    renderWithClient(<JobDetailPage />);

    await waitFor(() => {
      expect(screen.getByText(/40\s*%/i)).toBeInTheDocument();
      expect(screen.getByText("4 / 10")).toBeInTheDocument();
      expect(screen.getByText("32")).toBeInTheDocument();
      expect(screen.getByText(/Cancel/i)).toBeInTheDocument();
    });
  });

  it("renders completed state with data quality report and gap link", async () => {
    mockParams.id = "job-completed-123";
    vi.mocked(api.getJob).mockResolvedValueOnce({
      job_id: "job-completed-123",
      status: "completed",
      cells_total: 10,
      cells_done: 10,
      pct_complete: 100,
      places_found: 85,
      errors_count: 0,
      quality_report: {
        total_places: 85,
        open_places: 82,
        closed_places: 3,
        pct_with_website: 75.0,
        pct_with_real_website: 62.5,
        pct_with_phone: 91.0,
        pct_with_email: 45.0,
        pct_with_named_email: 30.0,
        pct_rating_coverage: 95.0,
        duplicates_removed: 5,
      },
      gap_summary: {
        job_id: "job-completed-123",
        category: "cafe",
        resolution: 8,
        total_hexes: 12,
        underserved_count: 4,
        balanced_count: 6,
        oversaturated_count: 2,
        insufficient_data_count: 0,
        area_median_rating: 4.2,
        best_hexes: [
          {
            h3_index: "88618925d3fffff",
            opportunity_score: 82.5,
            label: "underserved",
            reasons: ["0 competitors within 1 km", "12 offices nearby"],
          },
        ],
        saturated_hexes: [
          {
            h3_index: "88618925d1fffff",
            opportunity_score: 22.0,
            label: "oversaturated",
            reasons: ["15 competitors within 500m"],
          },
        ],
      },
    });

    renderWithClient(<JobDetailPage />);

    await waitFor(() => {
      expect(screen.getByText(/100\s*%/i)).toBeInTheDocument();
      expect(screen.getAllByText("85").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("Data Quality Report")).toBeInTheDocument();
      expect(screen.getByText("62.5%")).toBeInTheDocument();
      expect(screen.getByText(/View Interactive Gap Map/i)).toBeInTheDocument();
      expect(screen.getByText("Market Gap Insights")).toBeInTheDocument();
      expect(screen.getByText(/0 competitors within 1 km/i)).toBeInTheDocument();
    });
  });
});
