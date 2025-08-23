import { useEffect, useRef } from 'react';
import type { ChatMessage } from '../lib/types';
import { MessageContent } from './MessageContent';

type Props = {
  messages: ChatMessage[];
  theme?: 'light' | 'dark';
};

export function MessageList({ messages, theme = 'dark' }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    
    // Use requestAnimationFrame to ensure DOM has updated
    requestAnimationFrame(() => {
      el.scrollTo({
        top: el.scrollHeight,
        behavior: 'smooth'
      });
    });
  }, [messages]);

  return (
    <div ref={ref} className="messages">
      {messages.length === 0 ? (
        <div className="empty-state">
          <p>Start a conversation by typing a message below.</p>
        </div>
      ) : (
        <div className="messages-content">
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.role} ${(m as any).pending ? 'pending' : ''}`}>
              <div className="role">{m.role}</div>
              <div className="content">
                {(m as any).pending ? (
                  <span className="thinking"><span className="spinner" /> Thinking...</span>
                ) : (
                  <MessageContent content={m.content} theme={theme} />
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
