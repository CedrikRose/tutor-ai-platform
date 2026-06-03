import { useState, useEffect, useRef } from 'react';
import ExchangeList from './ExchangeList';
import MessageInput from './MessageInput';
import CourseSelectorV2 from './CourseSelectorV2';
import { API_URL, WS_URL } from '../config';
import './ChatWindow.css';

interface Exchange {
  exchange_id: string;
  exchange_number: number;
  user_question: string;
  assistant_answer: string;
  timestamp: string;
  tokens_used?: number;
  analyzed: boolean;
}

interface ChatWindowProps {
  conversationId: string; // Can be 'new' for new conversation
  onConversationUpdate: () => void;
  onConversationCreated: (id: string) => void;
  onToggleSidebar: () => void;
}

function ChatWindow({ conversationId, onConversationUpdate, onConversationCreated, onToggleSidebar }: ChatWindowProps) {
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [currentUserQuestion, setCurrentUserQuestion] = useState<string>('');
  const [streamingAnswer, setStreamingAnswer] = useState<string>('');
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [isWaitingForResponse, setIsWaitingForResponse] = useState<boolean>(false);
  const [actualConversationId, setActualConversationId] = useState<string | null>(null);
  const [courseContext, setCourseContext] = useState<any>(null);
  const [scrollToEnd, setScrollToEnd] = useState<boolean>(false);
  const wsRef = useRef<WebSocket | null>(null);
  
  // Store current streaming data in refs
  const currentStreamingQuestion = useRef<string>('');
  const currentStreamingAnswerRef = useRef<string>('');

  // Load conversation history (if not new)
  useEffect(() => {
    if (conversationId !== 'new') {
      setActualConversationId(conversationId);
      loadExchanges(conversationId);
    } else {
      setExchanges([]);
      setActualConversationId(null);
      setCourseContext(null);
    }
  }, [conversationId]);

  const loadExchanges = async (idToLoad?: string) => {
    const conversationIdToLoad = idToLoad || actualConversationId;
    if (!conversationIdToLoad || conversationIdToLoad === 'new') return;

    try {
      const response = await fetch(`${API_URL}/api/v2/conversations/${conversationIdToLoad}`, {
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        const loadedExchanges = data.exchanges || [];
        setExchanges(loadedExchanges);

        // Scroll to end when loading a conversation
        setTimeout(() => {
          setScrollToEnd(true);
        }, 100);

        // Auto-load course context from last exchange
        if (loadedExchanges.length > 0) {
          const lastExchange = loadedExchanges[loadedExchanges.length - 1];

          console.log('Last exchange loaded:', lastExchange);

          // Build context from last exchange
          const contextFromLastExchange = {
            course_id: lastExchange.course_id || null,
            max_lecture_sequence: lastExchange.max_lecture_sequence || null,
            material_types: lastExchange.material_types || null,
            selected_material_id: lastExchange.selected_material_id || null,
          };

          console.log('Context from last exchange:', contextFromLastExchange);

          // Only set if there's actual context (not all null)
          if (contextFromLastExchange.course_id ||
              contextFromLastExchange.max_lecture_sequence ||
              contextFromLastExchange.material_types ||
              contextFromLastExchange.selected_material_id) {
            setCourseContext(contextFromLastExchange);
            console.log('✅ Auto-loaded context:', contextFromLastExchange);
          } else {
            console.log('❌ No context to load (all null)');
          }
        } else {
          console.log('❌ No exchanges to load context from');
        }
      }
    } catch (error) {
      console.error('Error loading exchanges:', error);
    }
  };

  // WebSocket connection
  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}/api/v2/ws/chat`);

    ws.onopen = () => {
      console.log('WebSocket v2 connected');
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'token') {
        setIsWaitingForResponse(false);
        setIsStreaming(true);
        // Store in ref AND state
        currentStreamingAnswerRef.current += data.content;
        setStreamingAnswer((prev) => prev + data.content);
      } else if (data.type === 'done') {
        console.log('✅ Streaming done event received');
        console.log('Question from ref:', currentStreamingQuestion.current);
        console.log('Answer from ref length:', currentStreamingAnswerRef.current.length);
        
        // If this was a new conversation, save the ID
        if (conversationId === 'new' && data.conversation_id) {
          setActualConversationId(data.conversation_id);
          onConversationCreated(data.conversation_id);
        }

        // CRITICAL FIX: Update exchanges FIRST, then clear streaming states
        // This prevents the "empty message" bug
        setExchanges((currentExchanges) => {
          const newExchange: Exchange = {
            exchange_id: data.exchange_id || 'temp-' + Date.now(),
            exchange_number: currentExchanges.length + 1,
            user_question: currentStreamingQuestion.current,
            assistant_answer: currentStreamingAnswerRef.current,
            timestamp: new Date().toISOString(),
            tokens_used: data.tokens,
            analyzed: false
          };

          console.log('✅ New exchange created and added to list');
          
          // Clear streaming states AFTER adding to exchanges
          // Use setTimeout to ensure React processes the exchange update first
          setTimeout(() => {
            setIsStreaming(false);
            setIsWaitingForResponse(false);
            setStreamingAnswer('');
            setCurrentUserQuestion('');
            currentStreamingQuestion.current = '';
            currentStreamingAnswerRef.current = '';
            
            // Scroll to end after answer is complete
            setScrollToEnd(true);
          }, 50);
          
          return [...currentExchanges, newExchange];
        });
        
        onConversationUpdate();

      } else if (data.type === 'error') {
        console.error('WebSocket error:', data.message);
        setIsStreaming(false);
        setIsWaitingForResponse(false);
        setStreamingAnswer('');
        setCurrentUserQuestion('');
        currentStreamingQuestion.current = '';
        currentStreamingAnswerRef.current = '';
      }
    };

    ws.onclose = () => {
      console.log('WebSocket v2 disconnected');
      setIsConnected(false);
    };

    ws.onerror = (error) => {
      console.error('WebSocket v2 error:', error);
      setIsConnected(false);
    };

    wsRef.current = ws;

    return () => {
      ws.close();
    };
  }, [conversationId, onConversationCreated, onConversationUpdate]);

  const sendMessage = (message: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN && message.trim()) {
      setIsWaitingForResponse(true);
      setStreamingAnswer('');
      setCurrentUserQuestion(message);
      
      // Store in ref for later access
      currentStreamingQuestion.current = message;
      currentStreamingAnswerRef.current = '';

      // Send to backend
      wsRef.current.send(JSON.stringify({
        conversation_id: actualConversationId,
        message: message,
        course_context: courseContext || {
          course_id: null,
          max_lecture_sequence: null,
          material_types: null,
          selected_material_id: null
        }
      }));
    }
  };

  return (
    <div className="chat-window">
      <div className="chat-header">
        <div className="header-left">
          <button onClick={onToggleSidebar} className="hamburger-button" title="Chat-Liste">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path
                d="M3 12h18M3 6h18M3 18h18"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </button>
          <h2>Tutor AI</h2>
          <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
            {isConnected ? '● Online' : '○ Offline'}
          </span>
          {actualConversationId && (
            <span className="conversation-info">
              {exchanges.length} exchanges
            </span>
          )}
        </div>
      </div>

      <CourseSelectorV2
        conversationId={actualConversationId || 'new'}
        onContextChange={setCourseContext}
        initialContext={courseContext}
      />

      <ExchangeList
        exchanges={exchanges}
        currentUserQuestion={currentUserQuestion}
        streamingAnswer={streamingAnswer}
        isStreaming={isStreaming}
        isWaitingForResponse={isWaitingForResponse}
        scrollToEnd={scrollToEnd}
        onScrollComplete={() => setScrollToEnd(false)}
      />

      <MessageInput
        onSend={sendMessage}
        disabled={!isConnected || isStreaming || isWaitingForResponse}
      />
    </div>
  );
}

export default ChatWindow;
