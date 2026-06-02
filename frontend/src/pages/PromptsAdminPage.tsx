/**
 * Prompts Admin Page
 *
 * Password-protected page to view and edit all system prompts.
 */

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
    <div className="min-h-screen bg-gray-900">
      {/* Password Modal */}
      {showPasswordModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-8 max-w-md w-full mx-4">
            <h2 className="text-2xl font-bold text-white mb-6">Admin Zugang</h2>
            <form onSubmit={handleAuthenticate}>
              <div className="mb-4">
                <label className="block text-gray-300 mb-2">Passwort:</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-2 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                  placeholder="Passwort eingeben..."
                  autoFocus
                />
                {passwordError && (
                  <p className="text-red-400 text-sm mt-2">{passwordError}</p>
                )}
              </div>
              <button
                type="submit"
                disabled={isAuthenticating || !password}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isAuthenticating ? 'Authentifiziere...' : 'Einloggen'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Editor Modal */}
      {editingPrompt && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-lg w-full max-w-6xl max-h-[90vh] flex flex-col">
            {/* Header */}
            <div className="p-6 border-b border-gray-700">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h2 className="text-2xl font-bold text-white mb-2">
                    {editingPrompt.prompt_name}
                  </h2>
                  <p className="text-gray-400 text-sm mb-2">
                    {editingPrompt.description}
                  </p>
                  <div className="flex items-center gap-4 text-sm text-gray-500">
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
                  className="text-gray-400 hover:text-white text-2xl"
                >
                  ×
                </button>
              </div>
            </div>

            {/* Editor */}
            <div className="flex-1 p-6 overflow-hidden">
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className="w-full h-full bg-gray-900 text-white p-4 rounded border border-gray-700 focus:border-blue-500 focus:outline-none font-mono text-sm resize-none"
                placeholder="Prompt content..."
              />
            </div>

            {/* Footer */}
            <div className="p-6 border-t border-gray-700 flex justify-between items-center">
              <div className="text-sm text-gray-500">
                {editContent.length} Zeichen
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => setEditingPrompt(null)}
                  className="px-6 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded font-semibold"
                >
                  Abbrechen
                </button>
                <button
                  onClick={handleSave}
                  disabled={isSaving || editContent === editingPrompt.prompt_content}
                  className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded font-semibold disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
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
        <div className="fixed top-4 right-4 z-50 animate-fade-in">
          <div
            className={`px-6 py-3 rounded-lg shadow-lg ${
              toast.type === 'success'
                ? 'bg-green-600 text-white'
                : 'bg-red-600 text-white'
            }`}
          >
            {toast.message}
          </div>
        </div>
      )}

      {/* Main Content */}
      {isAuth && (
        <div className="container mx-auto px-4 py-8 max-w-7xl">
          {/* Header */}
          <div className="flex justify-between items-center mb-8">
            <div>
              <h1 className="text-3xl font-bold text-white mb-2">System Prompts</h1>
              <p className="text-gray-400">
                Alle System-Prompts verwalten und bearbeiten
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleReload}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded font-semibold"
              >
                ⟳ Neu laden
              </button>
              <button
                onClick={handleLogout}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded font-semibold"
              >
                Logout
              </button>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-900 border border-red-700 text-red-100 px-4 py-3 rounded mb-6">
              {error}
            </div>
          )}

          {/* Loading State */}
          {loading && (
            <div className="text-center py-12">
              <div className="inline-block animate-spin text-4xl text-blue-500 mb-4">⟳</div>
              <p className="text-gray-400">Lade Prompts...</p>
            </div>
          )}

          {/* Prompts Grid */}
          {!loading && prompts.length > 0 && (
            <div className="space-y-8">
              {Object.entries(CATEGORIES).map(([categoryKey, categoryInfo]) => {
                const categoryPrompts = promptsByCategory[categoryKey] || [];
                if (categoryPrompts.length === 0) return null;

                return (
                  <div key={categoryKey}>
                    <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                      <span className={`px-3 py-1 rounded text-sm ${categoryInfo.color}`}>
                        {categoryInfo.name}
                      </span>
                      <span className="text-gray-500 text-sm">
                        ({categoryPrompts.length})
                      </span>
                    </h2>
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                      {categoryPrompts.map((prompt) => (
                        <div
                          key={prompt.prompt_key}
                          className="bg-gray-800 rounded-lg p-6 border border-gray-700 hover:border-gray-600 transition-colors"
                        >
                          <div className="flex justify-between items-start mb-3">
                            <h3 className="text-lg font-semibold text-white">
                              {prompt.prompt_name}
                            </h3>
                            <button
                              onClick={() => handleEdit(prompt)}
                              className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded font-semibold"
                            >
                              Bearbeiten
                            </button>
                          </div>
                          {prompt.description && (
                            <p className="text-gray-400 text-sm mb-4">
                              {prompt.description}
                            </p>
                          )}
                          <div className="bg-gray-900 p-3 rounded text-xs text-gray-300 font-mono mb-3 max-h-32 overflow-y-auto">
                            {prompt.prompt_content.substring(0, 200)}
                            {prompt.prompt_content.length > 200 && '...'}
                          </div>
                          <div className="flex items-center gap-4 text-xs text-gray-500">
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
            <div className="text-center py-12 text-gray-400">
              Keine Prompts gefunden
            </div>
          )}
        </div>
      )}
    </div>
  );
}
