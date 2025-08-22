import { useEffect, useRef } from 'react';
import type { ChatMessage } from '../lib/types';

type Props = {
  messages: ChatMessage[];
};

export function MessageList({ messages }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages]);
  return (
    <div ref={ref} className="messages">
      {messages.map((m, i) => (
        <div key={i} className={`msg ${m.role} ${(m as any).pending ? 'pending' : ''}`}>
          <div className="role">{m.role}</div>
          <div className="content">
            {(m as any).pending ? (
              <span className="thinking"><span className="spinner" /> Thinking...</span>
            ) : (
              m.content
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
