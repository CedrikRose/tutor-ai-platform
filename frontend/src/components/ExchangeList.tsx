import { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import './MessageList.css';
import 'highlight.js/styles/github-dark.css';
import 'katex/dist/katex.min.css';

interface Exchange {
  exchange_id: string;
  exchange_number: number;
  user_question: string;
  assistant_answer: string;
  timestamp: string;
  tokens_used?: number;
  analyzed: boolean;
}

interface ExchangeListProps {
  exchanges: Exchange[];
  currentUserQuestion: string;
  streamingAnswer: string;
  isStreaming: boolean;
  isWaitingForResponse: boolean;
  scrollToEnd: boolean;
  onScrollComplete: () => void;
}

function ExchangeList({
  exchanges,
  currentUserQuestion,
  streamingAnswer,
  isStreaming,
  isWaitingForResponse,
  scrollToEnd,
  onScrollComplete
}: ExchangeListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const lastAnswerRef = useRef<HTMLDivElement>(null);

  // Smart scroll when answer is complete
  useEffect(() => {
    if (scrollToEnd && exchanges.length > 0) {
      // Small delay to ensure DOM is fully rendered
      setTimeout(() => {
        if (lastAnswerRef.current && messagesEndRef.current) {
          const answerElement = lastAnswerRef.current;
          const answerHeight = answerElement.offsetHeight;
          const viewportHeight = window.innerHeight;
          
          console.log('📏 Answer height:', answerHeight, 'Viewport height:', viewportHeight);
          
          // If answer is taller than 70% of viewport, scroll to start of answer
          // Otherwise scroll to end
          if (answerHeight > viewportHeight * 0.7) {
            console.log('📜 Long answer - scrolling to start');
            answerElement.scrollIntoView({ 
              behavior: 'smooth', 
              block: 'start' 
            });
          } else {
            console.log('📜 Short answer - scrolling to end');
            messagesEndRef.current.scrollIntoView({ 
              behavior: 'smooth' 
            });
          }
        } else {
          // Fallback: scroll to end
          messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
        }
        onScrollComplete();
      }, 100);
    }
  }, [scrollToEnd, exchanges.length, onScrollComplete]);

  // Auto-scroll during streaming
  useEffect(() => {
    if (isStreaming && streamingAnswer) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [streamingAnswer, isStreaming]);

  return (
    <div className="message-list">
      {/* Render exchanges */}
      {exchanges.map((exchange, index) => {
        const isLastExchange = index === exchanges.length - 1;
        
        return (
          <div key={exchange.exchange_id}>
            {/* User question */}
            <div className="message user">
              <div className="message-avatar">👤</div>
              <div className="message-content">
                <div className="message-text">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm, remarkMath]}
                    rehypePlugins={[rehypeHighlight, rehypeKatex]}
                  >
                    {exchange.user_question}
                  </ReactMarkdown>
                </div>
                <div className="message-timestamp">
                  {new Date(exchange.timestamp).toLocaleTimeString('de-DE', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </div>
              </div>
            </div>

            {/* Assistant answer - attach ref to last one */}
            <div 
              className="message assistant"
              ref={isLastExchange ? lastAnswerRef : null}
            >
              <div className="message-avatar">🤖</div>
              <div className="message-content">
                <div className="message-text">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm, remarkMath]}
                    rehypePlugins={[rehypeHighlight, rehypeKatex]}
                  >
                    {exchange.assistant_answer}
                  </ReactMarkdown>
                </div>
                <div className="message-timestamp">
                  {new Date(exchange.timestamp).toLocaleTimeString('de-DE', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                  {exchange.tokens_used && (
                    <span className="token-count"> · {exchange.tokens_used} tokens</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        );
      })}

      {/* Current user question (while waiting for answer) */}
      {currentUserQuestion && (
        <div className="message user">
          <div className="message-avatar">👤</div>
          <div className="message-content">
            <div className="message-text">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
              >
                {currentUserQuestion}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      )}

      {/* Waiting indicator */}
      {isWaitingForResponse && !streamingAnswer && (
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

      {/* Streaming answer */}
      {isStreaming && streamingAnswer && (
        <div className="message assistant streaming">
          <div className="message-avatar">🤖</div>
          <div className="message-content">
            <div className="message-text">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
              >
                {streamingAnswer}
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

export default ExchangeList;
