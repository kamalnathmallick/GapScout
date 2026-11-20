import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import LeadsPage from "@/app/leads/page";
import { api } from "@/lib/api";
import { LeadOut } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  api: {
    listLeads: vi.fn(),
    getDatasetHealth: vi.fn(),
    updateLeadStatus: vi.fn(),
  },
}));

const mockLeads: LeadOut[] = [
  {
    id: "lead-1",
    workspace_id: "ws-1",
    place_id: "place-1",
    place: {
      id: "place-1",
      workspace_id: "ws-1",
      name: "Artisan Cafe",
      category: "cafe",
      normalized_category: "cafe",
      address: "123 Indiranagar, Bangalore",
      phone_e164: "+919876543210",
      website: "https://artisancafe.example.com",
      website_domain: "artisancafe.example.com",
      email: "contact@artisancafe.example.com",
      rating: 4.6,
      review_count: 140,
      price_level: 2,
      latitude: 12.9716,
      longitude: 77.5946,
      h3_r8: "8860145b53fffff",
      is_closed: false,
      first_seen_at: new Date().toISOString(),
      last_seen_at: new Date().toISOString(),
    },
    status: "new",
    rule_score: 82.5,
    ml_score: 0.85,
    final_score: 83.2,
    score_breakdown: {
      reachability: { points: 11.2, max: 20, reason: "Phone and email found" },
    },
    notes: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "lead-2",
    workspace_id: "ws-1",
    place_id: "place-2",
    place: {
      id: "place-2",
      workspace_id: "ws-1",
      name: "Blue Tokai Coffee",
      category: "cafe",
      normalized_category: "cafe",
      address: "456 Koramangala, Bangalore",
      phone_e164: null,
      website: "https://bluetokai.example.com",
      website_domain: "bluetokai.example.com",
      email: null,
      rating: 4.8,
      review_count: 320,
      price_level: 3,
      latitude: 12.9716,
      longitude: 77.5946,
      h3_r8: "8860145b53fffff",
      is_closed: false,
      first_seen_at: new Date().toISOString(),
      last_seen_at: new Date().toISOString(),
    },
    status: "contacted",
    rule_score: 65.0,
    ml_score: null,
    final_score: 65.0,
    score_breakdown: {},
    notes: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

describe("LeadsPage Table Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getDatasetHealth).mockResolvedValue({
      total_labelled: 25,
      positives_count: 5,
      negatives_count: 20,
      positive_rate: 0.2,
      min_labels_required: 150,
      min_positives_required: 20,
      unlocked: false,
      labels_needed: 125,
      positives_needed: 15,
    });
  });

  it("renders leads table headers and items", async () => {
    vi.mocked(api.listLeads).mockResolvedValue({
      items: mockLeads,
      pagination: {
        total: 2,
        limit: 100,
        offset: 0,
        has_more: false,
      },
    });

    render(<LeadsPage />);

    expect(screen.getByText(/Lead Scorer & Outreach Pipeline/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Artisan Cafe")).toBeInTheDocument();
      expect(screen.getByText("Blue Tokai Coffee")).toBeInTheDocument();
    });

    // Score badges
    expect(screen.getByText("83")).toBeInTheDocument();
    expect(screen.getByText("65")).toBeInTheDocument();
  });

  it("filters leads when status dropdown changes", async () => {
    const firstLead = mockLeads[0];
    if (!firstLead) throw new Error("Missing test lead");

    vi.mocked(api.listLeads).mockResolvedValue({
      items: [firstLead],
      pagination: {
        total: 1,
        limit: 100,
        offset: 0,
        has_more: false,
      },
    });

    render(<LeadsPage />);

    const select = screen.getByDisplayValue("All Active");
    fireEvent.change(select, { target: { value: "new" } });

    await waitFor(() => {
      expect(api.listLeads).toHaveBeenCalledWith(
        expect.objectContaining({
          status: "new",
        }),
      );
    });
  });

  it("renders empty state when no leads are found", async () => {
    vi.mocked(api.listLeads).mockResolvedValueOnce({
      items: [],
      pagination: {
        total: 0,
        limit: 100,
        offset: 0,
        has_more: false,
      },
    });

    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText(/No leads match the selected criteria/i)).toBeInTheDocument();
    });
  });
});
