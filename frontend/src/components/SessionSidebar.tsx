import { Link } from 'react-router-dom';
import './SessionSidebar.css';

interface Session {
  conversation_id?: string;  // New API
  session_id?: string;        // Old API (backward compat)
  title: string;
  created_at: string;
  last_active: string;
  exchange_count?: number;    // New API
  message_count?: number;     // Old API (backward compat)
  total_tokens?: number;
}

interface SessionSidebarProps {
  sessions: Session[];
  currentSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onNewChat: () => void;
  onDeleteSession: (sessionId: string) => void;
  isOpen: boolean;
  onClose: () => void;
}

function SessionSidebar({
  sessions,
  currentSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  isOpen,
  onClose,
}: SessionSidebarProps) {
  return (
    <>
      {isOpen && <div className="sidebar-overlay" onClick={onClose} />}
      <div className={`session-sidebar ${isOpen ? 'open' : ''}`}>
      <div className="sidebar-header">
        <h2>Tutor AI</h2>
        <div className="header-buttons">
          <button onClick={onNewChat} className="new-chat-button" title="Neuer Chat">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 5v14M5 12h14"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </button>
          <button onClick={onClose} className="close-sidebar-button" title="Schließen">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path
                d="M18 6L6 18M6 6l12 12"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>
      </div>

      <div className="session-list">
        {sessions.length === 0 ? (
          <div className="empty-state">
            <p>Keine Chats vorhanden</p>
            <button onClick={onNewChat} className="btn-secondary">
              Ersten Chat starten
            </button>
          </div>
        ) : (
          sessions.map((session) => {
            const id = session.conversation_id || session.session_id || '';
            const count = session.exchange_count || session.message_count || 0;
            const label = session.exchange_count !== undefined ? 'Exchange' : 'Nachricht';

            return (
              <div
                key={id}
                className={`session-item ${id === currentSessionId ? 'active' : ''}`}
                onClick={() => onSelectSession(id)}
              >
                <div className="session-content">
                  <div className="session-title">{session.title}</div>
                  <div className="session-meta">
                    {count} {label}{count !== 1 ? (label === 'Exchange' ? 's' : 'en') : ''}
                  </div>
                </div>
                <button
                  className="delete-button"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm('Chat wirklich löschen?')) {
                      onDeleteSession(id);
                    }
                  }}
                  title="Chat löschen"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>
              </div>
            );
          })
        )}
      </div>

      <div className="sidebar-footer">
        <Link to="/about" className="about-link">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
            <path d="M12 16v-4M12 8h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          Info & Impressum
        </Link>
        <p className="version">Version 1.0</p>
      </div>
    </div>
    </>
  );
}

export default SessionSidebar;
