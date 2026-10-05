export interface User {
  id: number;
  email: string;
  full_name: string;
  role: string;
}

export interface AIAnalysis {
  category: string;
  intent: string;
  priority: string;
  priority_reason: string;
  sentiment: string;
  sentiment_confidence: number;
  short_summary: string;
  detailed_summary: string;
  reply_required: boolean;
  action_required: boolean;
}

export interface ExtractedInfo {
  customer_name?: string;
  company?: string;
  email_address?: string;
  phone_number?: string;
  order_number?: string;
  invoice_number?: string;
  product?: string;
  amount?: string;
  date?: string;
  deadline?: string;
  meeting_date?: string;
  location?: string;
  requested_action?: string;
}

export interface ActionItem {
  id: number;
  email_id: number;
  task: string;
  deadline_text?: string;
  status: string;
}

export interface Deadline {
  id: number;
  email_id: number;
  title: string;
  due_date: string;
  is_completed: boolean;
}

export interface AIReply {
  id: number;
  email_id: number;
  selected_tone: string;
  suggested_body: string;
  edited_body?: string;
  status: string;
  delivered?: boolean | null;
  delivery_note?: string | null;
}

export interface EmailListItem {
  id: number;
  sender_name: string;
  sender_email: string;
  subject: string;
  body_preview: string;
  received_at: string;
  is_read: boolean;
  is_starred: boolean;
  is_archived: boolean;
  category: string;
  priority: string;
  sentiment: string;
  reply_required: boolean;
  action_required: boolean;
  processing_status?: string;
  is_outbound?: boolean;
  reply_status?: string;
}

export interface EmailDetail extends EmailListItem {
  user_id: number;
  thread_id?: number;
  recipient_email: string;
  body_plain: string;
  body_html?: string;
  processing_status: string;
  processing_error?: string | null;
  ai_analysis?: AIAnalysis;
  extracted_info?: ExtractedInfo;
  action_items: ActionItem[];
  deadlines: Deadline[];
  ai_replies: AIReply[];
}

export interface DashboardOverview {
  total_emails: number;
  unread_emails: number;
  urgent_emails: number;
  reply_required_emails: number;
  customer_emails: number;
  sales_emails: number;
  support_emails: number;
  pending_actions: number;
  avg_response_time_hours?: number;
  sentiment_distribution?: Record<string, number>;
  priority_distribution?: Record<string, number>;
  replied_count?: number;
  complaint_count?: number;
  category_distribution: Record<string, number>;
  daily_volume?: { date: string; count: number }[];
  daily_activity?: { date: string; total: number; critical: number; replied: number }[];
  sentiment_trend?: { date: string; Positive: number; Neutral: number; Negative: number; Angry: number; Urgent: number }[];
  activity_heatmap?: { days: string[]; slots: string[]; grid: number[][] };
  sla?: { responded: number; pending: number; overdue: number };
  critical_queue?: CriticalQueueItem[];
  recent_emails?: EmailListItem[];
  recent_ai_actions?: RecentAIAction[];
  recent_urgent_emails: EmailListItem[];
  recent_actions: ActionItem[];
  upcoming_deadlines: Deadline[];
}

export interface CriticalQueueItem {
  id: number;
  subject: string;
  sender_name: string;
  received_at: string;
  category: string;
  priority: string;
  sentiment: string;
  confidence: number;
  summary: string;
}

export interface RecentAIAction {
  id: number;
  operation: string;
  provider: string;
  success: boolean;
  fallback_used: boolean;
  email_id?: number | null;
  subject?: string | null;
  created_at: string;
}

export interface ThreadDetail {
  id: number;
  subject: string;
  last_message_at: string;
  messages: EmailListItem[];
}
