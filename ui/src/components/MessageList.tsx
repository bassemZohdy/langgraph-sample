import { useEffect, useRef } from 'react';
import type { ChatMessage } from '../lib/types';
import { ReActMessage } from './ReActMessage';

type Props = {
  messages: ChatMessage[];
  theme?: 'light' | 'dark';
  showReasoningSteps?: boolean;
};

export function MessageList({ messages, theme = 'dark', showReasoningSteps = true }: Props) {
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
                  <ReActMessage 
                    content={m.content} 
                    theme={theme}
                    showReasoningSteps={showReasoningSteps}
                  />
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
