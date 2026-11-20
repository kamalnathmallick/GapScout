/**
 * Typed API Client for GapScout backend API v1.
 */

import {
  DNCOut,
  DatasetHealthOut,
  GapSummaryOut,
  GeneratedDraftOut,
  GridEstimateOut,
  HexMetricsResponse,
  JobCreateRequest,
  JobOut,
  JobProgressOut,
  LeadOut,
  LeadsListOut,
  OutreachDraft,
  OutreachEvent,
  PlacesListOut,
  TokenResponse,
  UserOut,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiClient {
  private getAuthToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("gapscout_access_token");
  }

  private setAuthTokens(accessToken: string, refreshToken: string) {
    if (typeof window === "undefined") return;
    localStorage.setItem("gapscout_access_token", accessToken);
    localStorage.setItem("gapscout_refresh_token", refreshToken);
  }

  public clearAuth() {
    if (typeof window === "undefined") return;
    localStorage.removeItem("gapscout_access_token");
    localStorage.removeItem("gapscout_refresh_token");
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = this.getAuthToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const url = `${API_BASE_URL}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorMessage = `HTTP error ${response.status}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.message || errorData.detail || errorMessage;
      } catch {
        // Fallback to status text
      }
      throw new Error(errorMessage);
    }

    return response.json() as Promise<T>;
  }

  // --- Auth Endpoints ---

  async register(payload: {
    email: string;
    password: string;
    full_name?: string;
    workspace_name: string;
  }): Promise<TokenResponse> {
    const data = await this.request<TokenResponse>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    this.setAuthTokens(data.access_token, data.refresh_token);
    return data;
  }

  async login(payload: { email: string; password: string }): Promise<TokenResponse> {
    const data = await this.request<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    this.setAuthTokens(data.access_token, data.refresh_token);
    return data;
  }

  async getMe(): Promise<UserOut> {
    return this.request<UserOut>("/api/v1/auth/me");
  }

  // --- Search Jobs Endpoints ---

  async estimateGrid(payload: JobCreateRequest): Promise<GridEstimateOut> {
    return this.request<GridEstimateOut>("/api/v1/jobs", {
      method: "POST",
      body: JSON.stringify({ ...payload, dry_run: true }),
    });
  }

  async createJob(payload: JobCreateRequest): Promise<JobOut> {
    return this.request<JobOut>("/api/v1/jobs", {
      method: "POST",
      body: JSON.stringify({ ...payload, dry_run: false }),
    });
  }

  async listJobs(limit = 20, offset = 0): Promise<JobOut[]> {
    return this.request<JobOut[]>(`/api/v1/jobs?limit=${limit}&offset=${offset}`);
  }

  async getJob(jobId: string): Promise<JobProgressOut> {
    return this.request<JobProgressOut>(`/api/v1/jobs/${jobId}`);
  }

  async cancelJob(jobId: string): Promise<JobOut> {
    return this.request<JobOut>(`/api/v1/jobs/${jobId}/cancel`, {
      method: "POST",
    });
  }

  async resumeJob(jobId: string): Promise<JobOut> {
    return this.request<JobOut>(`/api/v1/jobs/${jobId}/resume`, {
      method: "POST",
    });
  }

  // --- Places Endpoints ---

  async listPlaces(params?: {
    category?: string;
    min_rating?: number;
    has_website?: boolean;
    hex?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<PlacesListOut> {
    const q = new URLSearchParams();
    if (params?.category) q.set("category", params.category);
    if (params?.min_rating !== undefined) q.set("min_rating", String(params.min_rating));
    if (params?.has_website !== undefined) q.set("has_website", String(params.has_website));
    if (params?.hex) q.set("hex", params.hex);
    if (params?.search) q.set("search", params.search);
    if (params?.limit) q.set("limit", String(params.limit));
    if (params?.offset) q.set("offset", String(params.offset));

    const qs = q.toString() ? `?${q.toString()}` : "";
    return this.request<PlacesListOut>(`/api/v1/places${qs}`);
  }

  // --- Gap Analysis Endpoints ---

  async getGapHexes(jobId: string): Promise<HexMetricsResponse> {
    return this.request<HexMetricsResponse>(`/api/v1/gap/${jobId}/hexes`);
  }

  async getGapSummary(jobId: string): Promise<GapSummaryOut> {
    return this.request<GapSummaryOut>(`/api/v1/gap/${jobId}/summary`);
  }

  // --- Lead & Outreach Endpoints ---

  async listLeads(params?: {
    status?: string;
    min_score?: number;
    has_email?: boolean;
    hex?: string;
    include_dnc?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<LeadsListOut> {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    if (params?.min_score !== undefined) q.set("min_score", String(params.min_score));
    if (params?.has_email !== undefined) q.set("has_email", String(params.has_email));
    if (params?.hex) q.set("hex", params.hex);
    if (params?.include_dnc !== undefined) q.set("include_dnc", String(params.include_dnc));
    if (params?.limit) q.set("limit", String(params.limit));
    if (params?.offset) q.set("offset", String(params.offset));

    const qs = q.toString() ? `?${q.toString()}` : "";
    return this.request<LeadsListOut>(`/api/v1/leads${qs}`);
  }

  async getLead(leadId: string): Promise<LeadOut> {
    return this.request<LeadOut>(`/api/v1/leads/${leadId}`);
  }

  async updateLead(
    leadId: string,
    payload: { status?: string; notes?: string }
  ): Promise<LeadOut> {
    return this.request<LeadOut>(`/api/v1/leads/${leadId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  }

  async generateDraft(
    leadId: string,
    payload: { channel: "email" | "chat"; tone?: string; custom_offer?: string }
  ): Promise<GeneratedDraftOut> {
    return this.request<GeneratedDraftOut>(`/api/v1/leads/${leadId}/generate-draft`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async createDraft(
    leadId: string,
    payload: { channel: "email" | "chat"; body: string }
  ): Promise<OutreachDraft> {
    return this.request<OutreachDraft>(`/api/v1/leads/${leadId}/drafts`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async createEvent(
    leadId: string,
    payload: { event_type: string; features_snapshot?: Record<string, unknown> }
  ): Promise<OutreachEvent> {
    return this.request<OutreachEvent>(`/api/v1/leads/${leadId}/events`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async logOutcome(
    leadId: string,
    payload: { outcome: string; occurred_at?: string; notes?: string }
  ): Promise<OutreachEvent> {
    return this.request<OutreachEvent>(`/api/v1/leads/${leadId}/outcomes`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async importOutcomesCsv(
    csvContent: string
  ): Promise<{ imported: number; skipped: number; errors: string[] }> {
    return this.request<{ imported: number; skipped: number; errors: string[] }>(
      "/api/v1/leads/outcomes/import-csv",
      {
        method: "POST",
        body: JSON.stringify({ csv_content: csvContent }),
      }
    );
  }

  async getDatasetHealth(): Promise<DatasetHealthOut> {
    return this.request<DatasetHealthOut>("/api/v1/models/dataset/health");
  }

  // --- Do-Not-Contact (DNC) Endpoints ---

  async listDnc(): Promise<{ items: DNCOut[]; total: number }> {
    return this.request<{ items: DNCOut[]; total: number }>("/api/v1/dnc");
  }

  async addToDnc(payload: {
    email?: string;
    domain?: string;
    phone?: string;
    reason?: string;
  }): Promise<DNCOut> {
    return this.request<DNCOut>("/api/v1/dnc", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async deleteDnc(entryId: string): Promise<void> {
    return this.request<void>(`/api/v1/dnc/${entryId}`, {
      method: "DELETE",
    });
  }

  // --- Account Endpoints ---

  async exportAccountData(): Promise<Record<string, unknown>> {
    return this.request<Record<string, unknown>>("/api/v1/account/export");
  }

  async deleteAccountData(): Promise<{ message: string; status: string }> {
    return this.request<{ message: string; status: string }>("/api/v1/account/data", {
      method: "DELETE",
    });
  }
}

export const api = new ApiClient();
