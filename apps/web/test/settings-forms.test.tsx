import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import SettingsPage from "@/app/settings/page";
import { api } from "@/lib/api";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

vi.mock("@/lib/api", () => ({
  api: {
    getMe: vi.fn(),
    getOfferProfile: vi.fn(),
    updateOfferProfile: vi.fn(),
    getScoringWeights: vi.fn(),
    updateScoringWeights: vi.fn(),
    resetScoringWeights: vi.fn(),
    getWorkspaceCaps: vi.fn(),
    updateWorkspaceCaps: vi.fn(),
    getApiUsage: vi.fn(),
    exportAccountData: vi.fn(),
    deleteAccountData: vi.fn(),
    requestEmailVerification: vi.fn(),
    forgotPassword: vi.fn(),
  },
}));

describe("SettingsPage Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getMe).mockResolvedValue({
      id: "user-1",
      email: "owner@gapscout.test",
      full_name: "Workspace Owner",
      role: "owner",
      is_active: true,
      is_verified: true,
      workspace: {
        id: "ws-1",
        name: "Test Workspace",
        created_at: new Date().toISOString(),
      },
      created_at: new Date().toISOString(),
    });
    vi.mocked(api.getOfferProfile).mockResolvedValue({
      id: "profile-1",
      workspace_id: "ws-1",
      name: "Local Growth Offer",
      target_categories: ["cafe", "restaurant"],
      offer_description: "Help cafes get 30% more customers",
      min_rating: null,
      max_rating: null,
      target_regions: [],
      weights: {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
    vi.mocked(api.getScoringWeights).mockResolvedValue({
      weights: {
        pain: 25,
        fit: 25,
        timing: 15,
        reachability: 20,
        evidence: 15,
      },
      is_custom: false,
    });
    vi.mocked(api.getWorkspaceCaps).mockResolvedValue({
      max_cells_per_job: 200,
      max_places_per_job: 5000,
      daily_llm_cost_cap_usd: 2.0,
      data_retention_days: 90,
    });
    vi.mocked(api.getApiUsage).mockResolvedValue({
      total_calls: 15,
      prompt_tokens: 1200,
      completion_tokens: 450,
      total_cost_usd: 0.45,
      cost_today_usd: 0.45,
      daily_cost_cap_usd: 2.0,
      remaining_budget_today_usd: 1.55,
    });
  });

  it("renders tabs and navigates between them", async () => {
    render(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByText(/Workspace & Account Settings/i)).toBeInTheDocument();
      expect(screen.getByDisplayValue("Local Growth Offer")).toBeInTheDocument();
    });

    // Switch to Scoring Weights tab
    const weightsTab = screen.getByRole("button", { name: /Scoring Weights/i });
    fireEvent.click(weightsTab);

    await waitFor(() => {
      expect(screen.getByText(/Lead Scoring Formula Editor/i)).toBeInTheDocument();
      expect(screen.getByText(/Reset to Defaults/i)).toBeInTheDocument();
    });

    // Switch to Workspace Caps tab
    const capsTab = screen.getByRole("button", { name: /Workspace Caps/i });
    fireEvent.click(capsTab);

    await waitFor(() => {
      expect(screen.getByText(/Execution Caps & Data Retention/i)).toBeInTheDocument();
      expect(screen.getByDisplayValue("5000")).toBeInTheDocument();
    });
  });

  it("resets scoring weights to defaults when clicking reset", async () => {
    vi.mocked(api.resetScoringWeights).mockResolvedValue({
      weights: {
        pain: 25,
        fit: 25,
        timing: 15,
        reachability: 20,
        evidence: 15,
      },
      is_custom: false,
    });

    render(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByText(/Workspace & Account Settings/i)).toBeInTheDocument();
    });

    // Switch to Scoring Weights tab
    const weightsTab = screen.getByRole("button", { name: /Scoring Weights/i });
    fireEvent.click(weightsTab);

    await waitFor(() => {
      expect(screen.getByText(/Reset to Defaults/i)).toBeInTheDocument();
    });

    const resetBtn = screen.getByText(/Reset to Defaults/i);
    fireEvent.click(resetBtn);

    await waitFor(() => {
      expect(api.resetScoringWeights).toHaveBeenCalled();
    });
  });
});
