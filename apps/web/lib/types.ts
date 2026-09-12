export type ProviderStatus = "CONNECTED" | "NOT_CONFIGURED" | "ERROR";

export interface AIProvider {
  name: string;
  display_name: string;
  is_active: boolean;
  is_enabled: boolean;
  default_model: string;
  connection_status: ProviderStatus;
  available_models: string[];
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface Project {
  id: string;
  organization_id: string;
  owner_id?: string;
  name: string;
  description?: string;
  brand_voice?: string;
  target_audience?: string;
  industry?: string;
  language: string;
  country: string;
  tone?: string;
  content_guidelines?: string;
  seo_settings: Record<string, any>;
  publishing_settings: Record<string, any>;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface Article {
  id: string;
  project_id: string;
  author_id?: string;
  title: string;
  slug: string;
  topic: string;
  content: string;
  summary?: string;
  status: "DRAFT" | "GENERATING" | "IN_REVIEW" | "APPROVED" | "PUBLISHED" | "ARCHIVED";
  current_version: number;
  target_keywords: string[];
  estimated_reading_time: number;
  word_count: number;
  total_cost_usd: number;
  generated_by_provider?: string;
  generated_by_model?: string;
  content_strategy: Record<string, any>;
  outline: Record<string, any>;
  critic_evaluation: {
    score?: number;
    issues?: string[];
    strengths?: string[];
    needs_revision?: boolean;
  };
  created_at: string;
  updated_at: string;
}

export interface ArticleVersion {
  id: string;
  article_id: string;
  version_number: number;
  title: string;
  content: string;
  change_summary?: string;
  created_by: string;
  created_at: string;
}

export interface Source {
  id: string;
  article_id: string;
  title: string;
  url: string;
  domain: string;
  source_type: string;
  credibility_score: number;
  snippet?: string;
  is_verified: boolean;
  created_at: string;
}

export interface Claim {
  id: string;
  article_id: string;
  source_id?: string;
  claim_text: string;
  status: "VERIFIED" | "PARTIALLY_VERIFIED" | "UNVERIFIED" | "CONTRADICTED";
  confidence: number;
  notes?: string;
  created_at: string;
}

export interface SEOAnalysis {
  id: string;
  article_id: string;
  score: number;
  meta_title: string;
  meta_description: string;
  slug: string;
  focus_keywords: string[];
  heading_hierarchy_check: boolean;
  readability_score: number;
  faq_items: Array<{ question: string; answer: string }>;
  schema_markup: Record<string, any>;
  recommendations: string[];
  created_at: string;
}

export interface AnalyticsSummary {
  total_users: number;
  active_users: number;
  total_projects: number;
  total_articles: number;
  published_articles: number;
  total_llm_calls: number;
  total_cost_usd: number;
  provider_usage: Record<string, number>;
  agent_success_rate: number;
}
