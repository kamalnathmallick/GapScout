/**
 * TypeScript types for GapScout API v1.
 */

export interface WorkspaceOut {
  id: string;
  name: string;
  created_at: string;
}

export interface UserOut {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  workspace: WorkspaceOut;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: UserOut;
}

export interface BoundingBoxInput {
  min_lat: number;
  min_lon: number;
  max_lat: number;
  max_lon: number;
}

export interface JobCreateRequest {
  category: string;
  area_name?: string;
  bbox?: BoundingBoxInput;
  cell_size_m?: number;
  dry_run?: boolean;
}

export interface GridEstimateOut {
  cells_total: number;
  cell_size_m: number;
  area_km2: number;
  estimated_runtime_sec: number;
  estimated_cost_usd: number;
  area_name?: string;
  bbox: {
    min_lat: number;
    min_lon: number;
    max_lat: number;
    max_lon: number;
  };
}

export interface JobOut {
  id: string;
  workspace_id: string;
  category: string;
  area_name: string | null;
  status:
    | "pending"
    | "planning"
    | "running"
    | "paused"
    | "cancelling"
    | "cancelled"
    | "failed"
    | "completed";
  cells_total: number;
  cells_done: number;
  places_found: number;
  errors_count: number;
  error: string | null;
  params: Record<string, unknown>;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface QualityReport {
  total_places: number;
  open_places: number;
  closed_places: number;
  pct_with_website: number;
  pct_with_real_website: number;
  pct_with_phone: number;
  pct_with_email: number;
  pct_with_named_email: number;
  pct_rating_coverage: number;
  duplicates_removed: number;
}

export interface GapSummaryOut {
  job_id: string;
  category: string;
  resolution: number;
  total_hexes: number;
  underserved_count: number;
  balanced_count: number;
  oversaturated_count: number;
  insufficient_data_count: number;
  area_median_rating: number;
  best_hexes: Array<{
    h3_index: string;
    opportunity_score: number;
    label: string;
    reasons: string[];
  }>;
  saturated_hexes: Array<{
    h3_index: string;
    opportunity_score: number;
    label: string;
    reasons: string[];
  }>;
}

export interface JobProgressOut {
  job_id: string;
  status: string;
  cells_total: number;
  cells_done: number;
  pct_complete: number;
  places_found: number;
  errors_count: number;
  quality_report?: QualityReport | null;
  gap_summary?: GapSummaryOut | null;
}

export interface PlaceOut {
  id: string;
  workspace_id: string;
  name: string;
  category: string | null;
  normalized_category: string | null;
  address: string | null;
  phone_e164: string | null;
  website: string | null;
  website_domain: string | null;
  email: string | null;
  rating: number | null;
  review_count: number;
  price_level: number | null;
  h3_r8: string | null;
  is_closed: boolean;
  latitude: number | null;
  longitude: number | null;
  first_seen_at: string;
  last_seen_at: string;
}

export interface PaginationMeta {
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface PlacesListOut {
  items: PlaceOut[];
  pagination: PaginationMeta;
}

export interface HexMetricOut {
  id: string;
  search_job_id: string;
  category: string;
  h3_index: string;
  resolution: number;
  supply_count: number;
  density_per_km2: number | null;
  avg_rating: number | null;
  avg_review_count: number | null;
  demand_proxy: number | null;
  opportunity_score: number | null;
  label: "underserved" | "balanced" | "oversaturated" | "insufficient_data" | null;
  explanation: {
    top_reasons: string[];
    metrics: Record<string, unknown>;
  };
  computed_at: string;
}

export interface HexMetricsResponse {
  job_id: string;
  category: string;
  resolution: number;
  hexes: HexMetricOut[];
  geojson: {
    type: "FeatureCollection";
    features: Array<{
      type: "Feature";
      geometry: {
        type: "Polygon";
        coordinates: number[][][];
      };
      properties: Record<string, unknown>;
    }>;
  };
}

export interface ScoreComponent {
  points: number;
  max: number;
  reason: string;
}

export interface ScoreBreakdown {
  pain?: ScoreComponent;
  fit?: ScoreComponent;
  timing?: ScoreComponent;
  reachability?: ScoreComponent;
  evidence?: ScoreComponent;
  total?: number;
  [key: string]: unknown;
}

export interface OutreachDraft {
  id: string;
  lead_id: string;
  channel: "email" | "chat";
  body: string;
  created_at: string;
}

export interface OutreachEvent {
  id: string;
  lead_id: string;
  event_type: string;
  occurred_at: string;
  features_snapshot?: Record<string, unknown> | null;
}

export interface LeadOut {
  id: string;
  workspace_id: string;
  place_id: string;
  status:
    | "new"
    | "shortlisted"
    | "contacted"
    | "replied"
    | "meeting"
    | "converted"
    | "rejected"
    | "do_not_contact";
  rule_score: number | null;
  ml_score: number | null;
  final_score: number | null;
  score_breakdown: ScoreBreakdown;
  notes: string | null;
  place: PlaceOut | null;
  drafts?: OutreachDraft[];
  events?: OutreachEvent[];
  created_at: string;
  updated_at: string;
}

export interface LeadsListOut {
  items: LeadOut[];
  pagination: PaginationMeta;
}

export interface GeneratedDraftOut {
  id: string;
  lead_id: string;
  channel: string;
  body: string;
  word_count: number;
  char_count: number;
  mailto_link: string | null;
  wa_link: string | null;
  created_at: string;
}

export interface DNCOut {
  id: string;
  workspace_id: string;
  email: string | null;
  domain: string | null;
  phone: string | null;
  reason: string | null;
  created_at: string;
}

