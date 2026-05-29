/**
 * Analysis Types for Professor Dashboard
 */

export interface TopicCount {
  topic: string;
  count: number;
}

export interface SummaryStatistics {
  total_analyses: number;
  unique_students: number;
  total_knowledge_entries: number;
  total_feedback_entries: number;
  top_topics: TopicCount[];
  feedback_by_type: Record<string, number>;
}

export interface CourseSummary {
  summary_id: string;
  course_id: string;
  start_date: string;
  end_date: string;
  days_back: number;
  summary_text: string;
  statistics: SummaryStatistics | null;
  generated_at: string;
  generated_by: string;
}

export interface AnalysisListItem {
  analysis_id: string;
  session_id: string;
  analyzed_at: string;
  message_count: number;
  course_id: string | null;
  primary_model: string;
  required_secondary: boolean;
  tokens_used: number | null;
}

export interface AnalysisDetail extends AnalysisListItem {
  snapshot_id: string;
  analysis_text: string;
  secondary_model: string | null;
}

export interface StudentKnowledgeItem {
  knowledge_id: string;
  session_id: string;
  cookie_id: string;
  understood_concepts: string[];
  struggled_concept: string;
  error_description: string;
  solution_description: string;
  reference_message_ids: string[];
  created_at: string;
}

export interface FeedbackItem {
  feedback_id: string;
  session_id: string;
  feedback_type: string;
  feedback_text: string;
  sentiment: string | null;
  reference_message_ids: string[];
  created_at: string;
}

export interface TopicOverviewItem {
  topic: string;
  student_count: number;
  occurrence_count: number;
  session_ids: string[];
}

export interface TopicsOverview {
  course_id: string;
  date_range: {
    start: string;
    end: string;
  };
  topics: TopicOverviewItem[];
}

export interface ChatMessage {
  message_id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  rag_chunks: any | null;
}

export interface ChatSessionDetail {
  session_id: string;
  cookie_id: string;
  course_id: string | null;
  title: string | null;
  created_at: string;
  last_active: string;
  message_count: number;
  messages: ChatMessage[];
}

export interface EmailAutomation {
  automation_id: string;
  course_id: string;
  enabled: boolean;
  days_back: number;
  send_time_hour: number;
  recipient_emails: string[];
  created_at: string;
  last_sent_at: string | null;
  next_send_date: string | null;
}

export interface EmailAutomationConfig {
  course_id: string;
  days_back: number;
  recipient_emails: string[];
}

// Report Types
export interface ReportStatistics {
  total_findings: number;
  by_category: Record<string, number>;
  unique_conversations: number;
  topics_mentioned: Array<{
    topic: string;
    count: number;
  }>;
}

export interface Report {
  report_id: string;
  course_id: string;
  start_date: string;
  end_date: string;
  days_back: number;
  generated_at: string;
  statistics: ReportStatistics | null;
}

export interface ReportDetail extends Report {
  report_text: string;
  finding_ids: string[];
}

export interface ReportSettings {
  report_days_back: number;
  report_recipient_emails: string[];
  report_emails_enabled: boolean;
}
