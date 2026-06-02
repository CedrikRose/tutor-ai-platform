/**
 * API client for Prompts Admin functionality
 */

const API_BASE = '/api/prompts';

export interface Prompt {
  prompt_key: string;
  prompt_name: string;
  prompt_content: string;
  description?: string;
  category?: string;
  temperature?: number;
  max_tokens?: number;
  updated_at?: string;
  updated_by?: string;
  version?: number;
}

export interface AuthResponse {
  token: string;
  expires_in: number;
}

export interface UpdateResponse {
  status: string;
  prompt_key: string;
  version: number;
}

export interface ReloadResponse {
  status: string;
  count: number;
}

export interface HealthResponse {
  status: string;
  cache_size: number;
  last_reload: string | null;
  active_sessions: number;
}

class PromptsApiError extends Error {
  statusCode: number;

  constructor(statusCode: number, message: string) {
    super(message);
    this.name = 'PromptsApiError';
    this.statusCode = statusCode;
  }
}

/**
 * Authenticate with admin password
 */
export async function authenticate(password: string): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE}/authenticate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new PromptsApiError(401, 'Falsches Passwort');
    }
    throw new PromptsApiError(response.status, 'Authentifizierung fehlgeschlagen');
  }

  return response.json();
}

/**
 * List all prompts (requires authentication)
 */
export async function listPrompts(token: string): Promise<Prompt[]> {
  const response = await fetch(`${API_BASE}/list`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new PromptsApiError(401, 'Session abgelaufen - bitte neu einloggen');
    }
    throw new PromptsApiError(response.status, 'Fehler beim Laden der Prompts');
  }

  return response.json();
}

/**
 * Update a prompt (requires authentication)
 */
export async function updatePrompt(
  token: string,
  promptKey: string,
  content: string
): Promise<UpdateResponse> {
  const response = await fetch(`${API_BASE}/update`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({
      prompt_key: promptKey,
      prompt_content: content,
    }),
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new PromptsApiError(401, 'Session abgelaufen - bitte neu einloggen');
    }
    if (response.status === 404) {
      throw new PromptsApiError(404, 'Prompt nicht gefunden');
    }
    throw new PromptsApiError(response.status, 'Fehler beim Speichern');
  }

  return response.json();
}

/**
 * Reload all prompts from database (requires authentication)
 */
export async function reloadPrompts(token: string): Promise<ReloadResponse> {
  const response = await fetch(`${API_BASE}/reload`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new PromptsApiError(401, 'Session abgelaufen - bitte neu einloggen');
    }
    throw new PromptsApiError(response.status, 'Fehler beim Neuladen');
  }

  return response.json();
}

/**
 * Health check (no auth required)
 */
export async function healthCheck(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/health`);

  if (!response.ok) {
    throw new PromptsApiError(response.status, 'Health check fehlgeschlagen');
  }

  return response.json();
}

/**
 * Token management helpers
 */
const TOKEN_KEY = 'prompts_admin_token';
const TOKEN_EXPIRY_KEY = 'prompts_admin_token_expiry';

export function saveToken(token: string, expiresIn: number): void {
  const expiryTime = Date.now() + expiresIn * 1000;
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(TOKEN_EXPIRY_KEY, expiryTime.toString());
}

export function getToken(): string | null {
  const token = localStorage.getItem(TOKEN_KEY);
  const expiry = localStorage.getItem(TOKEN_EXPIRY_KEY);

  if (!token || !expiry) {
    return null;
  }

  // Check if token is expired
  if (Date.now() > parseInt(expiry)) {
    clearToken();
    return null;
  }

  return token;
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(TOKEN_EXPIRY_KEY);
}

export function isAuthenticated(): boolean {
  return getToken() !== null;
}
