import { useState, useRef, useEffect, type KeyboardEvent } from 'react';
import './MessageInput.css';

interface MessageInputProps {
  onSend: (message: string) => void;
  disabled: boolean;
}

function MessageInput({ onSend, disabled }: MessageInputProps) {
  const [message, setMessage] = useState<string>('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSend(message);
      setMessage('');
      // Reset height after sending
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // On Mobile: Enter = line break, only button sends
    // On Desktop: Shift+Enter = line break, Enter sends
    const isMobile = window.innerWidth <= 768;

    if (e.key === 'Enter' && !e.shiftKey && !isMobile) {
      // Only on Desktop: Enter sends
      e.preventDefault();
      handleSend();
    }
    // On Mobile: Enter automatically creates line break (no preventDefault)
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value);

    // Auto-grow textarea
    const textarea = e.target;
    textarea.style.height = 'auto';
    const newHeight = Math.min(textarea.scrollHeight, 200); // Max 200px
    textarea.style.height = `${newHeight}px`;
  };

  // Reset height when message is cleared
  useEffect(() => {
    if (!message && textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [message]);

  return (
    <div className="message-input">
      <textarea
        ref={textareaRef}
        value={message}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        placeholder={
          disabled
            ? 'Warte auf Antwort...'
            : window.innerWidth <= 768
              ? 'Stelle eine Frage...'
              : 'Stelle eine Frage... (Shift+Enter für neue Zeile)'
        }
        disabled={disabled}
        rows={1}
      />
      <button
        onClick={handleSend}
        disabled={disabled || !message.trim()}
        className="send-button"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
          <path
            d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
    </div>
  );
}

export default MessageInput;
