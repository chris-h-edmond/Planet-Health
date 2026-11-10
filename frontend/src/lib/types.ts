/**
 * Shared API types.
 *
 * The `Prediction` shape mirrors the output of the backend's
 * `predict_image()` helper exactly and must not be changed without versioning
 * the API.
 */

export interface User {
  id: number;
  full_name: string;
  email: string;
  created_at: string;
}

export interface AuthResponse {
  user: User;
  expires_at: string;
}

export interface StressProbabilities {
  healthy: number;
  stressed: number;
}

export interface StressPrediction {
  label: string;
  stress_score: number;
  score_scale: string;
  probabilities: StressProbabilities;
}

export interface GrowthPrediction {
  leaf_count: number;
  leaf_count_rounded: number;
  age_days: number;
}

export interface Prediction {
  stress: StressPrediction;
  growth: GrowthPrediction;
}

export interface AnalysisSummary {
  id: string;
  stress_label: string;
  stress_score: number;
  healthy_probability: number;
  stressed_probability: number;
  leaf_count: number;
  leaf_count_rounded: number;
  age_days: number;
  created_at: string;
}

export interface AnalysisDetail {
  id: string;
  created_at: string;
  stress: StressPrediction;
  growth: GrowthPrediction;
}

export interface PaginatedAnalyses {
  items: AnalysisSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DashboardStats {
  total_analyses: number;
  healthy_count: number;
  stressed_count: number;
  recent_analyses_count: number;
  recent_window_days: number;
  healthy_rate: number;
  average_stress_score: number;
  last_analysis_at: string | null;
}

export type ModelStatusState =
  | "not_configured"
  | "loading"
  | "ready"
  | "failed";

export interface ModelStatus {
  status: ModelStatusState;
  code: string;
  available: boolean;
  availability: "available" | "unavailable";
  message: string;
  detail: string | null;
  models: { stress: boolean; growth: boolean };
  device: string;
  checkpoints: { stress: string; growth: string };
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}
