"""Pydantic schemas for data validation and API payloads."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# Base config
class SchemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- AUTH SCHEMAS ---
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Argon2id hashed on server")
    full_name: str = Field(..., min_length=2, max_length=255)
    organization_name: Optional[str] = "Default Organization"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: str
    role: str
    organization_id: Optional[str] = None


class UserOut(SchemaBase):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    is_frozen: bool = False
    subscription_status: Optional[str] = "ACTIVE"
    subscription_expires_at: Optional[datetime] = None
    blocked_reason: Optional[str] = None
    company_name: Optional[str] = None
    is_superadmin: bool = False
    plan_id: Optional[str] = None
    db_name: Optional[str] = None


class UserRoleUpdate(BaseModel):
    role: str = Field(..., description="ADMIN, PORTAL_USER, or PUBLIC_USER")


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


# --- ORGANIZATION SCHEMAS ---
class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)


class OrganizationOut(SchemaBase):
    id: str
    name: str
    slug: str
    created_at: datetime


# --- PROJECT SCHEMAS ---
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    brand_voice: Optional[str] = "Professional, authoritative, engaging"
    target_audience: Optional[str] = "Tech professionals and decision makers"
    industry: Optional[str] = "Technology"
    language: str = "en"
    country: str = "US"
    tone: Optional[str] = "Informative"
    content_guidelines: Optional[str] = None
    seo_settings: Dict[str, Any] = Field(default_factory=dict)
    publishing_settings: Dict[str, Any] = Field(default_factory=dict)


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    brand_voice: Optional[str] = None
    target_audience: Optional[str] = None
    industry: Optional[str] = None
    language: Optional[str] = None
    country: Optional[str] = None
    tone: Optional[str] = None
    content_guidelines: Optional[str] = None
    seo_settings: Optional[Dict[str, Any]] = None
    publishing_settings: Optional[Dict[str, Any]] = None


class ProjectOut(SchemaBase):
    id: str
    organization_id: str
    owner_id: Optional[str]
    name: str
    description: Optional[str]
    brand_voice: Optional[str]
    target_audience: Optional[str]
    industry: Optional[str]
    language: str
    country: str
    tone: Optional[str]
    content_guidelines: Optional[str]
    seo_settings: Dict[str, Any]
    publishing_settings: Dict[str, Any]
    is_archived: bool
    created_at: datetime
    updated_at: datetime


# --- ARTICLE SCHEMAS ---
class ArticleCreateWizard(BaseModel):
    project_id: str
    topic: str = Field(..., min_length=5, description="Primary topic or subject")
    target_audience: Optional[str] = None
    content_goal: Optional[str] = "Educate, build authority, and rank for target search terms"
    research_depth: str = Field(default="standard", description="brief, standard, deep")
    target_keywords: List[str] = Field(default_factory=list)
    preferred_tone: Optional[str] = None


class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[str] = None
    change_summary: Optional[str] = "Manual update by user"


class ArticleVersionOut(SchemaBase):
    id: str
    article_id: str
    version_number: int
    title: str
    content: str
    change_summary: Optional[str]
    created_by: str
    created_at: datetime


class ArticleOut(SchemaBase):
    id: str
    project_id: str
    author_id: Optional[str]
    title: str
    slug: str
    topic: str
    content: str
    summary: Optional[str]
    status: str
    current_version: int
    target_keywords: List[str]
    estimated_reading_time: int
    word_count: int
    total_cost_usd: float
    generated_by_provider: Optional[str]
    generated_by_model: Optional[str]
    content_strategy: Dict[str, Any]
    outline: Dict[str, Any]
    critic_evaluation: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


# --- SOURCE & CLAIM SCHEMAS ---
class SourceOut(SchemaBase):
    id: str
    article_id: str
    title: str
    url: str
    domain: str
    source_type: str
    credibility_score: float
    snippet: Optional[str]
    is_verified: bool
    created_at: datetime


class ClaimOut(SchemaBase):
    id: str
    article_id: str
    source_id: Optional[str]
    claim_text: str
    status: str
    confidence: float
    notes: Optional[str]
    created_at: datetime


# --- PUBLIC FEEDBACK SCHEMAS ---
class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class CommentOut(SchemaBase):
    id: str
    article_id: str
    author_id: str
    author_name: str
    content: str
    created_at: datetime
    updated_at: datetime



# --- AGENT & WORKFLOW SCHEMAS ---
class AgentRunOut(SchemaBase):
    id: str
    article_id: str
    agent_name: str
    step_number: int
    status: str
    input_payload: Dict[str, Any]
    output_payload: Dict[str, Any]
    error_message: Optional[str]
    duration_ms: int
    created_at: datetime
    completed_at: Optional[datetime]


class WorkflowStartRequest(BaseModel):
    article_id: str


# --- PROVIDER & MODEL SCHEMAS ---
class ProviderStatusOut(BaseModel):
    name: str
    display_name: str
    is_active: bool
    is_enabled: bool
    default_model: str
    connection_status: str  # CONNECTED, NOT_CONFIGURED, ERROR
    last_health_check: Optional[datetime] = None
    available_models: List[str] = Field(default_factory=list)


class ProviderConfigureRequest(BaseModel):
    provider_name: str
    api_key: Optional[str] = Field(default=None, min_length=1)
    default_model: str = Field(..., min_length=1, max_length=255)


class SetActiveProviderRequest(BaseModel):
    provider_name: str
    model_name: Optional[str] = None


# --- SEO SCHEMAS ---
class SEOAnalysisOut(SchemaBase):
    id: str
    article_id: str
    score: int
    meta_title: str
    meta_description: str
    slug: str
    focus_keywords: List[str]
    heading_hierarchy_check: bool
    readability_score: float
    faq_items: List[Dict[str, str]]
    schema_markup: Dict[str, Any]
    recommendations: List[str]
    created_at: datetime


# --- PUBLISHING SCHEMAS ---
class WordPressPublishRequest(BaseModel):
    article_id: str
    site_url: str
    username: str
    application_password: str
    target_status: str = "draft"  # draft, publish


class PublishingJobOut(SchemaBase):
    id: str
    article_id: str
    platform: str
    target_status: str
    scheduled_at: Optional[datetime]
    published_url: Optional[str]
    status: str
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]


# --- AUDIT & ANALYTICS SCHEMAS ---
class AuditLogOut(SchemaBase):
    id: str
    user_id: Optional[str]
    organization_id: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Dict[str, Any]
    ip_address: Optional[str]
    created_at: datetime


class AnalyticsSummaryOut(BaseModel):
    total_users: int
    active_users: int
    total_projects: int
    total_articles: int
    published_articles: int
    total_llm_calls: int
    total_cost_usd: float
    provider_usage: Dict[str, int]
    agent_success_rate: float


class AdminUserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    role: str = Field(..., description="ADMIN or PORTAL_USER")


# --- MULTI-TENANT & SUBSCRIPTION SCHEMAS ---
class StudioSignupRequest(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=255)
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8)
    plan_id: str = Field(default="starter_studio")
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    razorpay_signature: Optional[str] = None


class SubscriptionPlanOut(SchemaBase):
    id: str
    name: str
    description: Optional[str] = None
    price_monthly_usd: float
    ai_provider_included: bool
    max_articles_monthly: int
    has_fact_checking: bool
    has_wordpress_syndication: bool
    has_advanced_seo: bool
    is_active: bool


class SubscriptionPlanUpdate(BaseModel):
    price_monthly_usd: Optional[float] = None
    name: Optional[str] = None
    description: Optional[str] = None
    ai_provider_included: Optional[bool] = None
    max_articles_monthly: Optional[int] = None
    has_fact_checking: Optional[bool] = None
    has_wordpress_syndication: Optional[bool] = None
    has_advanced_seo: Optional[bool] = None


class CompanyTenantOut(SchemaBase):
    id: str
    company_name: str
    slug: str
    admin_email: str
    db_name: str
    plan_id: str
    subscription_status: str
    subscription_expires_at: datetime
    is_blocked: bool
    blocked_reason: Optional[str] = None
    created_at: datetime


class CompanyFreezeRequest(BaseModel):
    reason: Optional[str] = "Blocked by administrator"


class CompanyRenewRequest(BaseModel):
    plan_id: Optional[str] = None
    extend_days: int = 30


class CompanySelfRenewRequest(BaseModel):
    email: Optional[EmailStr] = None
    password: str
    plan_id: Optional[str] = None
    extend_days: int = 30


class RazorpayCreateOrderRequest(BaseModel):
    plan_id: str
    extend_days: int = 30


class RazorpayOrderResponse(SchemaBase):
    order_id: str
    amount_paise: int
    currency: str
    key_id: str
    company_name: str
    admin_email: str
    plan_name: str
    extend_days: int
    is_test_mode: bool = False


class RazorpayVerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class RazorpayVerifyPaymentResponse(SchemaBase):
    success: bool
    message: str
    company_name: str
    subscription_status: str
    subscription_expires_at: datetime
    plan_id: str


class RazorpayCreateSignupOrderRequest(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    plan_id: str = Field(default="starter_studio")


class PaymentTransactionOut(SchemaBase):
    id: str
    company_tenant_id: Optional[str] = None
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    amount_paise: int
    amount_formatted: str
    currency: str
    status: str
    plan_id: str
    plan_name: str
    extend_days: int
    created_at: datetime
    receipt_url: Optional[str] = None


