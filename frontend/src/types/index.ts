export interface AuthStatus {
  demo_mode: boolean;
  google_connected: boolean;
  email: string | null;
  name: string | null;
  ai_provider: string;
  ai_configured: boolean;
  ai_message: string;
}

export interface EmailSummary {
  id: number;
  sender_name: string;
  sender_email: string;
  subject: string;
  snippet: string;
  received_at: string;
  category: string | null;
  urgency: string | null;
  status: string;
  is_processed: boolean;
  gmail_thread_id: string | null;
  draft_id: number | null;
  confidence_score: number | null;
  risk_level: string | null;
}

export interface Attachment {
  id: number;
  filename: string;
  mime_type: string;
  size: number;
  extracted_text: string;
}

export interface EmailAnalysis {
  intent?: string;
  required_action?: string;
  deadline?: string | null;
  sentiment?: string;
  key_points?: string[];
  entities?: string[];
  response_strategy?: string;
}

export interface AIResult {
  id: number;
  classification: { category?: string; confidence?: number; reason?: string };
  urgency: { urgency?: string; confidence?: number; reason?: string };
  analysis: EmailAnalysis;
  generated_reply: string;
  confidence_score: number | null;
  risk_score: number | null;
  risk_level: string | null;
  issues: string[];
  recommendation: string | null;
  routing_decision: string | null;
  processing_time: number | null;
  model_name: string | null;
  error_message: string | null;
  created_at: string;
}

export interface Draft {
  id: number;
  email_id: number;
  original_ai_draft: string;
  current_draft: string;
  status: string;
  reviewed_by_user: boolean;
  approved_at: string | null;
  sent_at: string | null;
  rejected_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ThreadMessage {
  id: number;
  sender_name: string;
  sender_email: string;
  subject: string;
  clean_body: string;
  received_at: string;
  is_current: boolean;
}

export interface ActivityItem {
  id: number;
  email_id: number | null;
  activity_type: string;
  message: string;
  created_at: string;
}

export interface FeedbackItem {
  id: number;
  email_id: number;
  ai_draft: string;
  human_final_reply: string;
  feedback_type: string;
  created_at: string;
}

export interface EmailDetail extends EmailSummary {
  body: string;
  clean_body: string;
  html_body: string | null;
  recipients: string[];
  cc: string[];
  labels: string[];
  in_reply_to: string | null;
  references: string | null;
  error_message: string | null;
  attachments: Attachment[];
  ai: AIResult | null;
  draft: Draft | null;
  thread: ThreadMessage[];
  activity: ActivityItem[];
  feedback: FeedbackItem[];
}

export interface EmailPage {
  items: EmailSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface ReviewItem {
  draft: Draft;
  email: EmailSummary;
}

export interface NamedCount {
  name: string;
  value: number;
}

export interface DayCount {
  date: string;
  count: number;
}

export interface DashboardStats {
  cards: {
    total: number;
    processed: number;
    needs_review: number;
    auto_sent: number;
    today: number;
  };
  by_category: NamedCount[];
  by_urgency: NamedCount[];
  routing: NamedCount[];
  over_time: DayCount[];
  recent_emails: EmailSummary[];
  review_queue: EmailSummary[];
  activity: ActivityItem[];
}

export interface Settings {
  auto_send_enabled: boolean;
  auto_send_max_risk: string;
  auto_send_min_confidence: number;
  tone: string;
  custom_instructions: string;
  signature: string;
  processing_enabled: boolean;
  polling_enabled: boolean;
  poll_interval_seconds: number;
  review_high_urgency: boolean;
  demo_mode: boolean;
  ai_provider: string;
  ai_configured: boolean;
  ai_message: string;
  google_connected: boolean;
  account_email: string;
  account_name: string;
  google_configured: boolean;
}

export interface SyncResult {
  created: number;
  updated: number;
  processed: number;
  failed: number;
  message: string;
}

export interface ActivityPage {
  items: ActivityItem[];
  total: number;
}
