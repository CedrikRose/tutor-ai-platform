import axios from 'axios';
import type {
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  User,
  Course,
  CreateCourseRequest,
  Homework,
  CreateHomeworkRequest,
  UploadSession,
  MaterialContentResponse,
} from '../types';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor to handle 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.pathname = '/dashboard/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  login: async (data: LoginRequest): Promise<TokenResponse> => {
    const response = await api.post<TokenResponse>('/auth/login', data);
    return response.data;
  },

  register: async (data: RegisterRequest): Promise<User> => {
    const response = await api.post<User>('/auth/register', data);
    return response.data;
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await api.get<User>('/auth/me');
    return response.data;
  },

  logout: async (): Promise<void> => {
    await api.post('/auth/logout');
  },
};

// Course API
export const courseApi = {
  getCourses: async (): Promise<Course[]> => {
    const response = await api.get<Course[]>('/professor/courses');
    return response.data;
  },

  getCourse: async (courseId: string): Promise<Course> => {
    const response = await api.get<Course>(`/professor/courses/${courseId}`);
    return response.data;
  },

  createCourse: async (data: CreateCourseRequest): Promise<Course> => {
    const response = await api.post<Course>('/professor/courses', data);
    return response.data;
  },

  updateCourse: async (courseId: string, data: Partial<CreateCourseRequest>): Promise<Course> => {
    const response = await api.patch<Course>(`/professor/courses/${courseId}`, data);
    return response.data;
  },

  deleteCourse: async (courseId: string): Promise<void> => {
    await api.delete(`/professor/courses/${courseId}`);
  },

  shareCourse: async (courseId: string, userEmail: string, permissionLevel: string): Promise<void> => {
    await api.post(`/courses/${courseId}/share`, { user_email: userEmail, permission_level: permissionLevel });
  },

  getMaterials: async (courseId: string): Promise<any[]> => {
    const response = await api.get(`/professor/courses/${courseId}/materials`);
    return response.data;
  },

  uploadMaterial: async (
    courseId: string,
    files: File[],
    materialType: string,
    customName?: string
  ): Promise<any> => {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    formData.append('material_type', materialType);
    if (customName) {
      formData.append('custom_name', customName);
    }

    const response = await api.post(`/professor/courses/${courseId}/materials/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  deleteMaterial: async (materialId: string): Promise<void> => {
    await api.delete(`/professor/materials/${materialId}`);
  },

  processMaterial: async (materialId: string): Promise<void> => {
    await api.post(`/professor/materials/${materialId}/process`);
  },

  getMaterialContent: async (materialId: string): Promise<MaterialContentResponse> => {
    const response = await api.get<MaterialContentResponse>(`/professor/materials/${materialId}/content`);
    return response.data;
  },

  updateMaterialContent: async (materialId: string, content: string): Promise<void> => {
    await api.put(`/professor/materials/${materialId}/content`, { content });
  },
};

// Homework API
export const homeworkApi = {
  getHomework: async (courseId: string): Promise<Homework[]> => {
    const response = await api.get<Homework[]>(`/courses/${courseId}/homework`);
    return response.data;
  },

  getHomeworkById: async (homeworkId: string): Promise<Homework> => {
    const response = await api.get<Homework>(`/homework/${homeworkId}`);
    return response.data;
  },

  createHomework: async (courseId: string, data: CreateHomeworkRequest): Promise<Homework> => {
    const response = await api.post<Homework>(`/courses/${courseId}/homework`, data);
    return response.data;
  },

  updateHomework: async (homeworkId: string, data: Partial<CreateHomeworkRequest>): Promise<Homework> => {
    const response = await api.patch<Homework>(`/homework/${homeworkId}`, data);
    return response.data;
  },

  deleteHomework: async (homeworkId: string): Promise<void> => {
    await api.delete(`/homework/${homeworkId}`);
  },
};

// File Upload API
export const fileApi = {
  uploadFiles: async (courseId: string, files: File[]): Promise<UploadSession> => {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));

    const response = await api.post<UploadSession>(`/courses/${courseId}/files/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getUploadSession: async (sessionId: string): Promise<UploadSession> => {
    const response = await api.get<UploadSession>(`/upload-sessions/${sessionId}`);
    return response.data;
  },

  confirmUpload: async (sessionId: string, decisions: Record<string, 'include' | 'skip'>): Promise<void> => {
    await api.post(`/upload-sessions/${sessionId}/confirm`, { file_decisions: decisions });
  },
};

// Admin API
export const adminApi = {
  getPendingUsers: async (): Promise<User[]> => {
    const response = await api.get<User[]>('/admin/users/pending');
    return response.data;
  },

  approveUser: async (userId: string): Promise<void> => {
    await api.post(`/admin/users/${userId}/approve`);
  },
};

export default api;
