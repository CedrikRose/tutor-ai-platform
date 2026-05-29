import { useState, useEffect } from 'react';
import { API_URL } from '../config';
import './AdminPanel.css';

interface AdminPanelProps {
  sessionId: string;
  isOpen: boolean;
  onClose: () => void;
}

interface SystemPromptData {
  system_prompt: string;
  last_rag_context: string | null;
  rag_chunks: Array<{
    chunk_id: string;
    file_name: string;
    content: string;
    distance: number;
    course_module?: string;
    content_type?: string;
    is_solution?: boolean;
  }>;
  session_context?: {
    course_module: string | null;
    homework_id: string | null;
    lecture_number: number | null;
  };
}

function AdminPanel({ sessionId, isOpen, onClose }: AdminPanelProps) {
  const [systemPrompt, setSystemPrompt] = useState<string>('');
  const [originalPrompt, setOriginalPrompt] = useState<string>('');
  const [ragContext, setRagContext] = useState<string>('');
  const [ragChunks, setRagChunks] = useState<Array<any>>([]);
  const [sessionContext, setSessionContext] = useState<any>(null);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveMessage, setSaveMessage] = useState<string>('');

  useEffect(() => {
    if (isOpen && sessionId) {
      loadAdminData();
    }
  }, [isOpen, sessionId]);

  const loadAdminData = async () => {
    try {
      const response = await fetch(`${API_URL}/api/admin/session/${sessionId}`, {
        credentials: 'include',
      });

      if (response.ok) {
        const data: SystemPromptData = await response.json();
        setSystemPrompt(data.system_prompt);
        setOriginalPrompt(data.system_prompt);
        setRagContext(data.last_rag_context || 'Noch keine RAG-Abfrage durchgeführt');
        setRagChunks(data.rag_chunks || []);
        setSessionContext(data.session_context || null);
      }
    } catch (error) {
      console.error('Error loading admin data:', error);
    }
  };

  const saveSystemPrompt = async () => {
    setIsSaving(true);
    setSaveMessage('');

    try {
      const response = await fetch('${API_URL}/api/admin/system-prompt', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ system_prompt: systemPrompt }),
      });

      if (response.ok) {
        const data = await response.json();
        setOriginalPrompt(systemPrompt);
        setSaveMessage(`✅ ${data.message || 'System Prompt gespeichert!'}`);
        setTimeout(() => setSaveMessage(''), 5000);
      } else {
        setSaveMessage('❌ Fehler beim Speichern');
      }
    } catch (error) {
      console.error('Error saving system prompt:', error);
      setSaveMessage('❌ Fehler beim Speichern');
    } finally {
      setIsSaving(false);
    }
  };

  const resetPrompt = () => {
    setSystemPrompt(originalPrompt);
  };

  if (!isOpen) return null;

  return (
    <div className="admin-overlay" onClick={onClose}>
      <div className="admin-panel" onClick={(e) => e.stopPropagation()}>
        <div className="admin-header">
          <h2>🔧 Admin-Panel</h2>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="admin-content">
          {/* System Prompt Section */}
          <div className="admin-section">
            <div className="section-header">
              <h3>System Prompt</h3>
              <div className="section-actions">
                <button
                  className="btn-secondary"
                  onClick={resetPrompt}
                  disabled={systemPrompt === originalPrompt}
                >
                  Zurücksetzen
                </button>
                <button
                  className="btn-primary"
                  onClick={saveSystemPrompt}
                  disabled={isSaving || systemPrompt === originalPrompt}
                >
                  {isSaving ? 'Speichern...' : 'Speichern'}
                </button>
              </div>
            </div>
            {saveMessage && <div className="save-message">{saveMessage}</div>}
            <textarea
              className="admin-textarea"
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              rows={12}
              placeholder="System Prompt bearbeiten..."
            />
          </div>

          {/* Session Context Section */}
          {sessionContext && (
            <div className="admin-section">
              <h3>Session-Kontext (RAG-Filter)</h3>
              <div className="context-info">
                <div className="context-item">
                  <span className="context-label">📚 Modul:</span>
                  <span className="context-value">{sessionContext.course_module || 'Nicht gesetzt'}</span>
                </div>
                <div className="context-item">
                  <span className="context-label">📝 Hausaufgabe:</span>
                  <span className="context-value">{sessionContext.homework_id || 'Nicht gesetzt'}</span>
                </div>
                <div className="context-item">
                  <span className="context-label">🎓 Vorlesung bis:</span>
                  <span className="context-value">{sessionContext.lecture_number || 'Alle'}</span>
                </div>
              </div>
            </div>
          )}

          {/* RAG Context Section */}
          <div className="admin-section">
            <h3>Aktueller RAG-Kontext</h3>
            <div className="rag-info">
              <p><strong>Anzahl Chunks:</strong> {ragChunks.length}</p>
            </div>
            <div className="rag-context-box">
              {ragContext}
            </div>
          </div>

          {/* RAG Chunks Detail */}
          {ragChunks.length > 0 && (
            <div className="admin-section">
              <h3>RAG Chunks Details</h3>
              <div className="chunks-list">
                {ragChunks.map((chunk, idx) => (
                  <div key={idx} className="chunk-item">
                    <div className="chunk-header">
                      <div className="chunk-info">
                        <span className="chunk-file">📄 {chunk.file_name}</span>
                        {chunk.is_solution && <span className="solution-badge">🔒 Musterlösung</span>}
                      </div>
                      <span className="chunk-distance">
                        Ähnlichkeit: {(1 - chunk.distance).toFixed(3)}
                      </span>
                    </div>
                    <div className="chunk-meta">
                      {chunk.course_module && <span>📚 {chunk.course_module}</span>}
                      {chunk.content_type && <span>📋 {chunk.content_type}</span>}
                    </div>
                    <pre className="chunk-content">{chunk.content}</pre>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default AdminPanel;
