import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import NewJobPage from "@/app/jobs/new/page";
import { api } from "@/lib/api";

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

vi.mock("@/lib/api", () => ({
  api: {
    estimateGrid: vi.fn(),
    createJob: vi.fn(),
  },
}));

describe("NewJobPage Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders form elements with default values", () => {
    render(<NewJobPage />);

    expect(screen.getByLabelText(/Target Category/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/City or Neighbourhood Name/i)).toHaveValue(
      "Indiranagar, Bangalore",
    );
    expect(screen.getByLabelText(/Search Cell Size/i)).toBeInTheDocument();
  });

  it("calls estimateGrid on mount with default values and displays estimates", async () => {
    vi.mocked(api.estimateGrid).mockResolvedValueOnce({
      cells_total: 9,
      cell_size_m: 1000,
      area_km2: 9.0,
      estimated_runtime_sec: 18,
      estimated_cost_usd: 0.05,
      area_name: "Indiranagar, Bangalore",
      bbox: {
        min_lat: 12.96,
        min_lon: 77.63,
        max_lat: 12.99,
        max_lon: 77.66,
      },
    });

    render(<NewJobPage />);

    await waitFor(() => {
      expect(api.estimateGrid).toHaveBeenCalledWith({
        category: "cafe",
        area_name: "Indiranagar, Bangalore",
        cell_size_m: 1000,
      });
    });

    await waitFor(() => {
      expect(screen.getByText("9 cells")).toBeInTheDocument();
      expect(screen.getByText("9.0 km²")).toBeInTheDocument();
      expect(screen.getByText("$0.05")).toBeInTheDocument();
    });
  });

  it("updates cell size slider and triggers new estimate", async () => {
    vi.mocked(api.estimateGrid).mockResolvedValue({
      cells_total: 4,
      cell_size_m: 1500,
      area_km2: 9.0,
      estimated_runtime_sec: 8,
      estimated_cost_usd: 0.02,
      bbox: { min_lat: 12.96, min_lon: 77.63, max_lat: 12.99, max_lon: 77.66 },
    });

    render(<NewJobPage />);

    const slider = screen.getByRole("slider");
    fireEvent.change(slider, { target: { value: "1500" } });

    await waitFor(() => {
      expect(screen.getByText(/Search Cell Size: 1500m/i)).toBeInTheDocument();
    });
  });

  it("submits the form successfully and navigates to job detail", async () => {
    vi.mocked(api.estimateGrid).mockResolvedValueOnce({
      cells_total: 9,
      cell_size_m: 1000,
      area_km2: 9.0,
      estimated_runtime_sec: 18,
      estimated_cost_usd: 0.05,
      bbox: { min_lat: 12.96, min_lon: 77.63, max_lat: 12.99, max_lon: 77.66 },
    });

    vi.mocked(api.createJob).mockResolvedValueOnce({
      id: "job-12345",
      workspace_id: "ws-1",
      category: "cafe",
      area_name: "Indiranagar, Bangalore",
      status: "pending",
      cells_total: 9,
      cells_done: 0,
      places_found: 0,
      errors_count: 0,
      error: null,
      params: {},
      started_at: null,
      finished_at: null,
      created_at: new Date().toISOString(),
    });

    render(<NewJobPage />);

    // Wait for estimate to load
    await waitFor(() => {
      expect(screen.getByText("9 cells")).toBeInTheDocument();
    });

    // Button should be disabled until TOS checkbox is checked
    const submitBtn = screen.getByText(/Confirm and Start Analysis/i).closest("button");
    expect(submitBtn).toBeDisabled();

    // Check TOS consent checkbox
    const tosCheckbox = screen.getByTestId("tos-checkbox");
    fireEvent.click(tosCheckbox);

    // Button should now be enabled
    expect(submitBtn).not.toBeDisabled();

    const form = screen.getByTestId("new-job-form");
    fireEvent.submit(form);

    await waitFor(() => {
      expect(api.createJob).toHaveBeenCalledWith({
        category: "cafe",
        area_name: "Indiranagar, Bangalore",
        cell_size_m: 1000,
      });
      expect(mockPush).toHaveBeenCalledWith("/jobs/job-12345");
    });
  });
});
