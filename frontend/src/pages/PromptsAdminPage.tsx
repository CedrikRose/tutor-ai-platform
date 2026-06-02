/**
 * Prompts Admin Page
 *
 * Password-protected page to view and edit all system prompts.
 */

import './PromptsAdminPage.css';
import React, { useState, useEffect } from 'react';
import {
  authenticate,
  listPrompts,
  updatePrompt,
  reloadPrompts,
  saveToken,
  getToken,
  clearToken,
  isAuthenticated,
  type Prompt,
} from '../api/prompts';

// Category display names and colors
const CATEGORIES = {
  chat: { name: 'Chat', color: 'bg-blue-100 text-blue-800' },
  analysis: { name: 'Analyse', color: 'bg-purple-100 text-purple-800' },
  report: { name: 'Report', color: 'bg-green-100 text-green-800' },
  material: { name: 'Material', color: 'bg-orange-100 text-orange-800' },
};

export default function PromptsAdminPage() {
  // Authentication state
  const [isAuth, setIsAuth] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [password, setPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [isAuthenticating, setIsAuthenticating] = useState(false);

  // Prompts state
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Editor state
  const [editingPrompt, setEditingPrompt] = useState<Prompt | null>(null);
  const [editContent, setEditContent] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Toast notification state
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  // Check authentication on mount
  useEffect(() => {
    if (isAuthenticated()) {
      setIsAuth(true);
      loadPrompts();
    } else {
      setShowPasswordModal(true);
    }
  }, []);

  // Auto-hide toast after 3 seconds
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type });
  };

  const handleAuthenticate = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError('');
    setIsAuthenticating(true);

    try {
      const response = await authenticate(password);
      saveToken(response.token, response.expires_in);
      setIsAuth(true);
      setShowPasswordModal(false);
      setPassword('');
      await loadPrompts();
      showToast('Erfolgreich eingeloggt');
    } catch (err: any) {
      setPasswordError(err.message || 'Authentifizierung fehlgeschlagen');
    } finally {
      setIsAuthenticating(false);
    }
  };

  const loadPrompts = async () => {
    const token = getToken();
    if (!token) {
      setIsAuth(false);
      setShowPasswordModal(true);
      return;
    }

    setLoading(true);
    setError('');

    try {
      const data = await listPrompts(token);
      setPrompts(data);
    } catch (err: any) {
      if (err.statusCode === 401) {
        clearToken();
        setIsAuth(false);
        setShowPasswordModal(true);
      } else {
        setError(err.message || 'Fehler beim Laden der Prompts');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (prompt: Prompt) => {
    setEditingPrompt(prompt);
    setEditContent(prompt.prompt_content);
    setSaveSuccess(false);
  };

  const handleSave = async () => {
    if (!editingPrompt) return;

    const token = getToken();
    if (!token) {
      setIsAuth(false);
      setShowPasswordModal(true);
      return;
    }

    setIsSaving(true);

    try {
      const response = await updatePrompt(token, editingPrompt.prompt_key, editContent);

      // Update local state
      setPrompts(prompts.map(p =>
        p.prompt_key === editingPrompt.prompt_key
          ? { ...p, prompt_content: editContent, version: response.version, updated_by: 'admin' }
          : p
      ));

      setSaveSuccess(true);
      showToast(`Prompt gespeichert (Version ${response.version})`);

      // Close editor after 1 second
      setTimeout(() => {
        setEditingPrompt(null);
        setSaveSuccess(false);
      }, 1000);
    } catch (err: any) {
      if (err.statusCode === 401) {
        clearToken();
        setIsAuth(false);
        setShowPasswordModal(true);
      } else {
        showToast(err.message || 'Fehler beim Speichern', 'error');
      }
    } finally {
      setIsSaving(false);
    }
  };

  const handleReload = async () => {
    const token = getToken();
    if (!token) {
      setIsAuth(false);
      setShowPasswordModal(true);
      return;
    }

    try {
      const response = await reloadPrompts(token);
      showToast(`${response.count} Prompts neu geladen`);
      await loadPrompts();
    } catch (err: any) {
      if (err.statusCode === 401) {
        clearToken();
        setIsAuth(false);
        setShowPasswordModal(true);
      } else {
        showToast(err.message || 'Fehler beim Neuladen', 'error');
      }
    }
  };

  const handleLogout = () => {
    clearToken();
    setIsAuth(false);
    setShowPasswordModal(true);
    setPrompts([]);
  };

  // Group prompts by category
  const promptsByCategory = prompts.reduce((acc, prompt) => {
    const category = prompt.category || 'other';
    if (!acc[category]) acc[category] = [];
    acc[category].push(prompt);
    return acc;
  }, {} as Record<string, Prompt[]>);

  return (
    <div className="prompts-admin">
      {/* Password Modal */}
      {showPasswordModal && (
        <div className="modal-overlay">
          <div className="password-modal">
            <h2 className="">Admin Zugang</h2>
            <form onSubmit={handleAuthenticate}>
              <div className="mb-4">
                <label className="">Passwort:</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className=""
                  placeholder="Passwort eingeben..."
                  autoFocus
                />
                {passwordError && (
                  <p className="password-error">{passwordError}</p>
                )}
              </div>
              <button
                type="submit"
                disabled={isAuthenticating || !password}
                className="btn-primary"
              >
                {isAuthenticating ? 'Authentifiziere...' : 'Einloggen'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Editor Modal */}
      {editingPrompt && (
        <div className="modal-overlay">
          <div className="editor-modal">
            {/* Header */}
            <div className="editor-header">
              <div className="editor-header-content">
                <div className="editor-title">
                  <h2 className="">
                    {editingPrompt.prompt_name}
                  </h2>
                  <p className="editor-description">
                    {editingPrompt.description}
                  </p>
                  <div className="editor-meta">
                    <span>Key: {editingPrompt.prompt_key}</span>
                    {editingPrompt.temperature && (
                      <span>Temperature: {editingPrompt.temperature}</span>
                    )}
                    {editingPrompt.max_tokens && (
                      <span>Max Tokens: {editingPrompt.max_tokens}</span>
                    )}
                    {editingPrompt.version && (
                      <span>Version: {editingPrompt.version}</span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => setEditingPrompt(null)}
                  className="btn-close"
                >
                  ×
                </button>
              </div>
            </div>

            {/* Editor */}
            <div className="editor-body">
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className="editor-textarea"
                placeholder="Prompt content..."
              />
            </div>

            {/* Footer */}
            <div className="editor-footer">
              <div className="editor-char-count">
                {editContent.length} Zeichen
              </div>
              <div className="editor-actions">
                <button
                  onClick={() => setEditingPrompt(null)}
                  className="btn-cancel"
                >
                  Abbrechen
                </button>
                <button
                  onClick={handleSave}
                  disabled={isSaving || editContent === editingPrompt.prompt_content}
                  className="btn-save"
                >
                  {isSaving ? (
                    <>
                      <span className="animate-spin">⟳</span>
                      Speichert...
                    </>
                  ) : saveSuccess ? (
                    <>✓ Gespeichert</>
                  ) : (
                    'Speichern'
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Toast Notification */}
      {toast && (
        <div className="toast">
          <div className={`toast-content ${toast.type === 'success' ? 'toast-success' : 'toast-error'}`}>
            {toast.message}
          </div>
        </div>
      )}

      {/* Main Content */}
      {isAuth && (
        <div className="prompts-container">
          {/* Header */}
          <div className="prompts-header">
            <div>
              <h1 className="">System Prompts</h1>
              <p className="">
                Alle System-Prompts verwalten und bearbeiten
              </p>
            </div>
            <div className="editor-actions">
              <button
                onClick={handleReload}
                className="btn-secondary"
              >
                ⟳ Neu laden
              </button>
              <button
                onClick={handleLogout}
                className="btn-secondary"
              >
                Logout
              </button>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          {/* Loading State */}
          {loading && (
            <div className="loading-container">
              <div className="loading-spinner">⟳</div>
              <p className="">Lade Prompts...</p>
            </div>
          )}

          {/* Prompts Grid */}
          {!loading && prompts.length > 0 && (
            <div className="">
              {Object.entries(CATEGORIES).map(([categoryKey, categoryInfo]) => {
                const categoryPrompts = promptsByCategory[categoryKey] || [];
                if (categoryPrompts.length === 0) return null;

                return (
                  <div key={categoryKey}>
                    <h2 className="category-header">
                      <span className={`category-badge ${categoryKey}`}>
                        {categoryInfo.name}
                      </span>
                      <span className="category-count">
                        ({categoryPrompts.length})
                      </span>
                    </h2>
                    <div className="prompts-grid">
                      {categoryPrompts.map((prompt) => (
                        <div
                          key={prompt.prompt_key}
                          className="prompt-card"
                        >
                          <div className="prompt-card-header">
                            <h3 className="">
                              {prompt.prompt_name}
                            </h3>
                            <button
                              onClick={() => handleEdit(prompt)}
                              className="btn-edit"
                            >
                              Bearbeiten
                            </button>
                          </div>
                          {prompt.description && (
                            <p className="prompt-description">
                              {prompt.description}
                            </p>
                          )}
                          <div className="prompt-preview">
                            {prompt.prompt_content.substring(0, 200)}
                            {prompt.prompt_content.length > 200 && '...'}
                          </div>
                          <div className="prompt-meta">
                            <span>Key: {prompt.prompt_key}</span>
                            {prompt.temperature && (
                              <span>Temp: {prompt.temperature}</span>
                            )}
                            {prompt.version && <span>v{prompt.version}</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Empty State */}
          {!loading && prompts.length === 0 && (
            <div className="empty-state">
              Keine Prompts gefunden
            </div>
          )}
        </div>
      )}
    </div>
  );
}
