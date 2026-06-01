/**
 * Analysis API Service
 */
import axios from 'axios';
import type {
  CourseSummary,
  AnalysisListItem,
  AnalysisDetail,
  StudentKnowledgeItem,
  FeedbackItem,
  TopicsOverview,
  ChatSessionDetail,
  EmailAutomation,
  EmailAutomationConfig,
  Report,
  ReportDetail,
  ReportSettings,
} from '../types/analysis';

// Create axios instance with auth
const api = axios.create({
  baseURL: '/api',
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ============================================================================
// Summaries
// ============================================================================

export const generateSummary = async (
  courseId: string,
  daysBack: number
): Promise<CourseSummary> => {
  const response = await api.post('/professor/summaries/generate', {
    course_id: courseId,
    days_back: daysBack,
  });
  return response.data;
};

export const getSummaries = async (
  courseId: string,
  limit: number = 20
): Promise<CourseSummary[]> => {
  const response = await api.get('/professor/summaries', {
    params: { course_id: courseId, limit },
  });
  return response.data;
};

// ============================================================================
// Analyses
// ============================================================================

export const getAnalyses = async (params: {
  course_id?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}): Promise<AnalysisListItem[]> => {
  const response = await api.get('/professor/analyses', { params });
  return response.data;
};

export const getAnalysisDetail = async (
  analysisId: string
): Promise<AnalysisDetail> => {
  const response = await api.get(`/professor/analyses/${analysisId}`);
  return response.data;
};

// ============================================================================
// Student Knowledge
// ============================================================================

export const getStudentKnowledge = async (params: {
  course_id?: string;
  cookie_id?: string;
  topic?: string;
  limit?: number;
  offset?: number;
}): Promise<StudentKnowledgeItem[]> => {
  const response = await api.get('/professor/student-knowledge', {
    params,
  });
  return response.data;
};

export const getTopicsOverview = async (
  courseId: string,
  daysBack: number = 7
): Promise<TopicsOverview> => {
  const response = await api.get('/professor/topics-overview', {
    params: { course_id: courseId, days_back: daysBack },
  });
  return response.data;
};

// ============================================================================
// Feedback
// ============================================================================

export const getFeedback = async (params: {
  course_id?: string;
  feedback_type?: string;
  sentiment?: string;
  limit?: number;
  offset?: number;
}): Promise<FeedbackItem[]> => {
  const response = await api.get('/professor/feedback', { params });
  return response.data;
};

// ============================================================================
// Chat Viewer
// ============================================================================

export const getChatSession = async (
  sessionId: string
): Promise<ChatSessionDetail> => {
  const response = await api.get(`/professor/chat/${sessionId}`);
  return response.data;
};

// ============================================================================
// Email Automation
// ============================================================================

export const createEmailAutomation = async (
  config: EmailAutomationConfig
): Promise<EmailAutomation> => {
  const response = await api.post('/professor/email-automation', config);
  return response.data;
};

export const getEmailAutomations = async (
  courseId?: string
): Promise<EmailAutomation[]> => {
  const response = await api.get('/professor/email-automation', {
    params: courseId ? { course_id: courseId } : {},
  });
  return response.data;
};

export const toggleEmailAutomation = async (
  automationId: string
): Promise<{ automation_id: string; enabled: boolean }> => {
  const response = await api.patch(
    `/professor/email-automation/${automationId}/toggle`
  );
  return response.data;
};

export const deleteEmailAutomation = async (
  automationId: string
): Promise<void> => {
  await api.delete(`/professor/email-automation/${automationId}`);
};

// ============================================================================
// Reports
// ============================================================================

export const generateReport = async (
  courseId: string,
  endDate?: string,
  daysBack?: number
): Promise<ReportDetail> => {
  const response = await api.post('/professor/reports/generate', {
    course_id: courseId,
    end_date: endDate || new Date().toISOString().split('T')[0],
    days_back: daysBack,
  });
  return response.data;
};

export const getReports = async (
  courseId: string,
  limit: number = 10,
  offset: number = 0
): Promise<Report[]> => {
  const response = await api.get('/professor/reports', {
    params: { course_id: courseId, limit, offset },
  });
  return response.data;
};

export const getReportDetail = async (
  reportId: string
): Promise<ReportDetail> => {
  const response = await api.get(`/professor/reports/${reportId}`);
  return response.data;
};

export const updateReportSettings = async (
  courseId: string,
  settings: Partial<ReportSettings>
): Promise<void> => {
  await api.patch(`/professor/courses/${courseId}/report-settings`, settings);
};
