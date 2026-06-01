import { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import './MessageList.css';
import 'highlight.js/styles/github-dark.css';
import 'katex/dist/katex.min.css';

interface Message {
  message_id: string;
  role: string;
  content: string;
  timestamp: string;
}

interface MessageListProps {
  messages: Message[];
  streamingMessage: string;
  isStreaming: boolean;
  isWaitingForResponse: boolean;
}

function MessageList({ messages, streamingMessage, isStreaming, isWaitingForResponse }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingMessage]);

  return (
    <div className="message-list">
      {messages.map((msg) => (
        <div key={msg.message_id} className={`message ${msg.role}`}>
          <div className="message-avatar">
            {msg.role === 'user' ? '👤' : '🤖'}
          </div>
          <div className="message-content">
            <div className="message-text">
              <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeHighlight, rehypeKatex]}
              >
                {msg.content}
              </ReactMarkdown>
            </div>
            <div className="message-timestamp">
              {new Date(msg.timestamp).toLocaleTimeString('de-DE', {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </div>
          </div>
        </div>
      ))}

      {isWaitingForResponse && !streamingMessage && (
        <div className="message assistant">
          <div className="message-avatar">🤖</div>
          <div className="message-content">
            <div className="loading-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      )}

      {isStreaming && streamingMessage && (
        <div className="message assistant streaming">
          <div className="message-avatar">🤖</div>
          <div className="message-content">
            <div className="message-text">
              <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeHighlight, rehypeKatex]}
              >
                {streamingMessage}
              </ReactMarkdown>
            </div>
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
}

export default MessageList;
