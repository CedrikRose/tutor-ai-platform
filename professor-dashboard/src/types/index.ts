export interface User {
  user_id: string;
  email: string;
  full_name: string | null;
  institution: string | null;
  role: string;
  is_active: boolean;
  email_verified: boolean;
  created_at: string;
  last_login: string | null;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
  institution: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Course {
  course_id: string;
  course_code: string;
  course_name: string;
  semester: string | null;
  academic_year: number | null;
  owner_user_id: string;
  is_active: boolean;
  student_access: boolean;
  max_lecture_number: number | null;
  description: string | null;
  created_at: string;
  updated_at: string;
  report_days_back?: number;
  report_recipient_emails?: string[];
  report_emails_enabled?: boolean;
}

export interface CreateCourseRequest {
  course_name: string;
  semester?: string;
  student_access: boolean;
  course_code?: string;
  academic_year?: number;
  description?: string;
  max_lecture_number?: number;
}

export interface Homework {
  homework_id: string;
  course_id: string;
  homework_code: string;
  title: string | null;
  description: string | null;
  sequence_number: number | null;
  start_date: string | null;
  due_date: string | null;
  max_points: number | null;
  is_published: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateHomeworkRequest {
  homework_code: string;
  title?: string;
  description?: string;
  sequence_number?: number;
  start_date?: string;
  due_date?: string;
  max_points?: number;
  is_published: boolean;
}

export interface FileAnalysis {
  filename: string;
  content_type: string;
  importance: string;
  sequence_number: number | null;
  reason: string;
  user_decision: 'pending' | 'include' | 'skip';
}

export interface UploadSession {
  upload_session_id: string;
  course_id: string;
  total_files: number;
  analyzed_files: number;
  status: 'analyzing' | 'ready' | 'processing' | 'completed';
  file_analyses: FileAnalysis[];
  created_at: string;
}

export interface MaterialFile {
  file_id: string;
  filename: string;
  file_path: string;
  file_size: number | null;
}

export interface CourseMaterial {
  material_id: string;
  course_id: string;
  material_type: 'lecture_slide' | 'homework' | 'tutorium' | 'other';
  display_name: string;
  original_filename: string;
  sequence_number: number | null;
  file_count: number;
  files: MaterialFile[];


  processed_at: string | null;
  created_at: string;
}

export interface UploadMaterialRequest {
  material_type: 'lecture_slide' | 'homework' | 'tutorium' | 'other';
  custom_name?: string;
}

export interface MaterialContentResponse {
  material_id: string;
  material_type: 'lecture_slide' | 'homework' | 'tutorium' | 'other';
  display_name: string;
  content: string;
  is_editable: boolean;
}
