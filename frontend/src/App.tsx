import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import ChatWindow from './components/ChatWindow';
import SessionSidebar from './components/SessionSidebar';
import About from './pages/About';
import PromptsAdminPage from './pages/PromptsAdminPage';
import Cookies from 'js-cookie';
import { v4 as uuidv4 } from 'uuid';
import { API_URL } from './config';
import './App.css';

interface Conversation {
  conversation_id: string;
  title: string;
  created_at: string;
  last_active: string;
  exchange_count: number;
  total_tokens: number;
}

function ChatApp() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [cookieId, setCookieId] = useState<string>('');
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(true);

  // Initialize cookie ID
  useEffect(() => {
    let id = Cookies.get('ai_tutor_user_id');
    if (!id) {
      id = uuidv4();
      Cookies.set('ai_tutor_user_id', id, { expires: 365 });
    }
    setCookieId(id);
  }, []);

  // Load conversations (API v2)
  const loadConversations = async () => {
    if (!cookieId) return;

    try {
      const response = await fetch(`${API_URL}/api/v2/conversations`, {
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        setConversations(data);
      }
    } catch (error) {
      console.error('Error loading conversations:', error);
    }
  };

  useEffect(() => {
    if (cookieId) {
      loadConversations();
    }
  }, [cookieId]);

  // Handle window resize - manage sidebar state based on screen size
  useEffect(() => {
    const handleResize = () => {
      const isMobile = window.innerWidth <= 768;
      if (!isMobile) {
        // On desktop, sidebar should always be open
        setIsSidebarOpen(true);
      }
      // On mobile, keep current state (user can toggle manually)
    };

    // Set initial state
    handleResize();

    // Add listener
    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Start new chat (no API call needed - conversation created on first message!)
  const startNewChat = () => {
    setCurrentConversationId('new'); // Special marker for new conversation
  };

  // Delete conversation
  const deleteConversation = async (conversationId: string) => {
    try {
      const response = await fetch(`${API_URL}/api/v2/conversations/${conversationId}`, {
        method: 'DELETE',
        credentials: 'include',
      });

      if (response.ok) {
        if (currentConversationId === conversationId) {
          setCurrentConversationId(null);
        }
        await loadConversations();
      }
    } catch (error) {
      console.error('Error deleting conversation:', error);
    }
  };

  return (
    <div className="app">
      <SessionSidebar
        sessions={conversations}
        currentSessionId={currentConversationId}
        onSelectSession={(id) => {
          setCurrentConversationId(id);
          setIsSidebarOpen(false); // Close sidebar on mobile after selection
        }}
        onNewChat={startNewChat}
        onDeleteSession={deleteConversation}
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
      />

      <div className="main-content">
        {currentConversationId ? (
          <ChatWindow
            conversationId={currentConversationId}
            onConversationUpdate={loadConversations}
            onConversationCreated={(id) => {
              setCurrentConversationId(id);
              loadConversations();
            }}
            onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
          />
        ) : (
          <div className="welcome-screen">
            <div className="welcome-content">
              <h1>🤖 Tutor AI</h1>
              <p>Dein persönlicher Programmier-Tutor</p>
              <button onClick={startNewChat} className="btn-primary">
                Neuen Chat starten
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ChatApp />} />
        <Route path="/about" element={<About />} />
        <Route path="/prompts" element={<PromptsAdminPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
