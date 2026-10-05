from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- Auth Schemas ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    company: Optional[str] = None
    job_title: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class EmailVerifyRequest(BaseModel):
    token: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    company: Optional[str] = None
    job_title: Optional[str] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    verify_token: Optional[str] = None

# --- AI & Extraction Schemas ---
class ExtractedInfoSchema(BaseModel):
    customer_name: Optional[str] = None
    company: Optional[str] = None
    email_address: Optional[str] = None
    phone_number: Optional[str] = None
    order_number: Optional[str] = None
    invoice_number: Optional[str] = None
    product: Optional[str] = None
    amount: Optional[str] = None
    date: Optional[str] = None
    deadline: Optional[str] = None
    meeting_date: Optional[str] = None
    location: Optional[str] = None
    requested_action: Optional[str] = None

    class Config:
        from_attributes = True

class ActionItemSchema(BaseModel):
    id: int
    email_id: int
    task: str
    deadline_text: Optional[str] = None
    due_date: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DeadlineSchema(BaseModel):
    id: int
    email_id: int
    title: str
    due_date: str
    source_phrase: Optional[str] = None
    is_completed: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AIAnalysisSchema(BaseModel):
    category: str
    intent: str
    priority: str
    priority_reason: str
    sentiment: str
    sentiment_confidence: float
    short_summary: str
    detailed_summary: str
    reply_required: bool
    action_required: bool
    provider: Optional[str] = "heuristic"
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AIReplySchema(BaseModel):
    id: int
    email_id: int
    selected_tone: str
    suggested_body: str
    edited_body: Optional[str] = None
    status: str
    provider: Optional[str] = "heuristic"
    model: Optional[str] = None
    version: Optional[int] = 1
    created_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    reject_reason: Optional[str] = None
    sent_email_id: Optional[int] = None
    delivered: Optional[bool] = None  # set only by the approve endpoint: was the e-mail really sent?
    delivery_note: Optional[str] = None

    class Config:
        from_attributes = True

class SmartReplyRequest(BaseModel):
    tone: Optional[str] = "Professional"
    custom_instructions: Optional[str] = None
    reject_reason: Optional[str] = None

class SmartReplyApproveRequest(BaseModel):
    edited_body: Optional[str] = None

class SmartReplyRejectRequest(BaseModel):
    reason: Optional[str] = None

# --- Email Schemas ---
class EmailCreate(BaseModel):
    sender_email: EmailStr
    sender_name: str
    recipient_email: Optional[EmailStr] = None
    subject: str
    body_plain: str
    body_html: Optional[str] = None
    received_at: Optional[datetime] = None
    message_id: Optional[str] = None
    in_reply_to: Optional[str] = None

class EmailImportBatch(BaseModel):
    emails: List[EmailCreate]

class EmailListItem(BaseModel):
    id: int
    user_id: int
    thread_id: Optional[int] = None
    sender_name: str
    sender_email: str
    recipient_email: str
    subject: str
    body_preview: str
    received_at: datetime
    is_read: bool
    is_starred: bool
    is_archived: bool
    is_outbound: bool = False
    reply_status: str = "not_required"
    processing_status: str = "queued"
    category: Optional[str] = "Unprocessed"
    priority: Optional[str] = "MEDIUM"
    sentiment: Optional[str] = "Neutral"
    reply_required: Optional[bool] = False
    action_required: Optional[bool] = False

    class Config:
        from_attributes = True

class EmailDetailResponse(BaseModel):
    id: int
    user_id: int
    thread_id: Optional[int] = None
    sender_id: Optional[int] = None
    sender_email: str
    sender_name: str
    recipient_email: str
    subject: str
    body_plain: str
    body_html: Optional[str] = None
    received_at: datetime
    message_id: Optional[str] = None
    in_reply_to: Optional[str] = None
    is_outbound: bool = False
    content_hash: Optional[str] = None
    reply_status: str = "not_required"
    replied_at: Optional[datetime] = None
    is_read: bool
    is_starred: bool
    is_archived: bool
    processing_status: str
    processing_error: Optional[str] = None
    raw_eml_path: Optional[str] = None
    
    ai_analysis: Optional[AIAnalysisSchema] = None
    extracted_info: Optional[ExtractedInfoSchema] = None
    action_items: List[ActionItemSchema] = []
    deadlines: List[DeadlineSchema] = []
    ai_replies: List[AIReplySchema] = []

    class Config:
        from_attributes = True

class EmailThreadListItem(BaseModel):
    id: int
    subject: str
    snippet: Optional[str] = None
    unread_count: int = 0
    last_message_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True

class EmailThreadDetailResponse(BaseModel):
    id: int
    subject: str
    snippet: Optional[str] = None
    unread_count: int = 0
    last_message_at: datetime
    messages: List[EmailListItem] = []

    class Config:
        from_attributes = True

# --- AI Assistant Schemas ---
class AIAssistantQuery(BaseModel):
    question: str
    conversation_id: Optional[int] = None

class AIAssistantResponse(BaseModel):
    answer: str
    conversation_id: int
    cited_emails: List[EmailListItem] = []
    filters: Optional[Dict[str, Any]] = None

# --- Notifications Schemas ---
class NotificationResponse(BaseModel):
    id: int
    user_id: int
    email_id: Optional[int] = None
    type: str
    title: str
    message: str
    dedupe_key: Optional[str] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

class NotificationPreferenceSchema(BaseModel):
    urgent_email: bool = True
    customer_complaint: bool = True
    reply_required: bool = True
    upcoming_deadline: bool = True
    action_item: bool = True
    ai_completed: bool = False

    class Config:
        from_attributes = True

class NotificationPreferenceUpdate(BaseModel):
    urgent_email: Optional[bool] = None
    customer_complaint: Optional[bool] = None
    reply_required: Optional[bool] = None
    upcoming_deadline: Optional[bool] = None
    action_item: Optional[bool] = None
    ai_completed: Optional[bool] = None

# --- Analytics & Dashboard Schemas ---
class DashboardOverview(BaseModel):
    total_emails: int
    unread_emails: int
    urgent_emails: int
    reply_required_emails: int
    customer_emails: int
    sales_emails: int
    support_emails: int
    pending_actions: int
    avg_response_time_hours: float
    replied_count: int = 0
    complaint_count: int = 0
    category_distribution: Dict[str, int]
    sentiment_distribution: Dict[str, int]
    priority_distribution: Dict[str, int]
    daily_volume: List[Dict[str, Any]] = []
    daily_activity: List[Dict[str, Any]] = []
    sentiment_trend: List[Dict[str, Any]] = []
    activity_heatmap: Dict[str, Any] = {}
    sla: Dict[str, int] = {}
    critical_queue: List[Dict[str, Any]] = []
    recent_emails: List[EmailListItem] = []
    recent_ai_actions: List[Dict[str, Any]] = []
    recent_urgent_emails: List[EmailListItem] = []
    recent_actions: List[ActionItemSchema] = []
    upcoming_deadlines: List[DeadlineSchema] = []

# --- Admin Schemas ---
class CategorySchema(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    color: str
    is_active: bool
    is_system: bool

    class Config:
        from_attributes = True

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color: Optional[str] = "#64748b"
    is_active: bool = True

class CategoryUpdate(BaseModel):
    description: Optional[str] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None

class SystemSettingSchema(BaseModel):
    key: str
    value: Any
    default: Any
    description: str
    is_overridden: bool
    updated_at: Optional[datetime] = None

class SystemSettingUpdate(BaseModel):
    value: Any

class UserRoleUpdate(BaseModel):
    role: str

class UserStatusUpdate(BaseModel):
    is_active: bool

class AILogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    email_id: Optional[int] = None
    operation: str
    provider: str
    model: Optional[str] = None
    success: bool
    fallback_used: bool
    latency_ms: int
    error: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    action: str
    resource: str
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True

class AdminStatsResponse(BaseModel):
    total_users: int
    active_users: int
    total_emails: int
    total_threads: int
    total_ai_analyses: int
    total_smart_replies: int
    total_ai_logs: int
    ai_errors_count: int
    effective_ai_provider: str


class ProcessingFailedItem(BaseModel):
    id: int
    user_id: int
    processing_error: Optional[str] = None
    retry_count: int = 0
    received_at: datetime


class AdminProcessingResponse(BaseModel):
    by_status: Dict[str, int]
    failed: List[ProcessingFailedItem]


class AdminUsageRow(BaseModel):
    name: str
    calls: int
    failures: int
    fallbacks: int
    avg_latency_ms: int


class AdminUsageResponse(BaseModel):
    total_calls: int
    failed_calls: int
    error_rate: float
    calls_last_24h: int
    by_operation: List[AdminUsageRow]
    by_provider: List[AdminUsageRow]
