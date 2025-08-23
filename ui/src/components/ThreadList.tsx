import { useEffect, useState } from 'react';
import { apiDeleteThread, apiListThreads, apiGetThreadMessages, type ThreadInfo } from '../lib/api';
import { PlusIcon, TrashIcon } from './Icons';

type Props = {
  onSelect: (threadId: string) => void;
  onNewThread?: () => void;
  version?: number; // when this changes, refresh list
  onChanged?: () => void; // notify parent to refresh elsewhere
  selectedThreadId?: string; // currently selected thread
};

type ThreadWithName = ThreadInfo & {
  displayName: string;
};

function generateThreadName(firstMessage: string): string {
  if (!firstMessage.trim()) return "New conversation";
  
  // Remove common prefixes and clean up
  let name = firstMessage
    .replace(/^(hi|hello|hey|hi there|hello there)\s*/i, "")
    .replace(/^(can you|could you|please|help me)\s*/i, "")
    .trim();
  
  // Limit to first 3-4 words, max 30 characters
  const words = name.split(/\s+/).slice(0, 4);
  let result = words.join(" ");
  
  if (result.length > 30) {
    result = result.substring(0, 27) + "...";
  }
  
  // Capitalize first letter
  result = result.charAt(0).toUpperCase() + result.slice(1);
  
  return result || "New conversation";
}

export function ThreadList({ onSelect, onNewThread, version = 0, onChanged, selectedThreadId }: Props) {
  const [threads, setThreads] = useState<ThreadWithName[]>([]);
  const [loadingNames, setLoadingNames] = useState<Set<string>>(new Set());

  async function load() {
    const list = await apiListThreads();
    
    // Initialize threads with basic names
    const threadsWithNames: ThreadWithName[] = list.map(thread => ({
      ...thread,
      displayName: `Thread ${thread.thread_id.split('_')[1]?.substring(0, 6) || 'new'}`
    }));
    
    setThreads(threadsWithNames);
    
    // Load names for threads with messages asynchronously
    for (const thread of list) {
      if (thread.message_count && thread.message_count > 0) {
        loadThreadName(thread.thread_id);
      }
    }
  }

  async function loadThreadName(threadId: string) {
    if (loadingNames.has(threadId)) return;
    
    setLoadingNames(prev => new Set(prev).add(threadId));
    
    try {
      const messages = await apiGetThreadMessages(threadId);
      if (messages.length > 0) {
        const firstUserMessage = messages.find(m => m.role === 'user');
        if (firstUserMessage) {
          const name = generateThreadName(firstUserMessage.content);
          setThreads(prev => prev.map(t => 
            t.thread_id === threadId 
              ? { ...t, displayName: name }
              : t
          ));
        }
      }
    } catch (error) {
      console.error('Failed to load thread name:', error);
    } finally {
      setLoadingNames(prev => {
        const next = new Set(prev);
        next.delete(threadId);
        return next;
      });
    }
  }

  async function remove(threadId: string) {
    if (!confirm(`Delete thread ${threadId}?`)) return;
    try {
      await apiDeleteThread(threadId);
      await load();
      onChanged?.();
    } catch (e) {
      alert('Failed to delete thread');
    }
  }

  useEffect(() => {
    load();
    // Optional: small polling to catch external changes
    const id = setInterval(load, 8000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    load();
  }, [version]);

  return (
    <section>
      <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0 }}>Threads</h3>
        <button className="icon-btn" title="New thread" onClick={onNewThread}><PlusIcon /></button>
      </div>
      <div className="threads-container">
        {threads.length === 0 && <div className="muted">No threads yet.</div>}
        {threads.map((t) => (
          <div 
            key={t.thread_id} 
            className={`thread-item ${t.thread_id === selectedThreadId ? 'selected' : ''}`}
            onClick={() => onSelect(t.thread_id)}
          >
            <div className="thread-content">
              <div className="thread-name">{t.displayName}</div>
              <div className="thread-meta">
                <span className="thread-id">{t.thread_id.split('_')[1]?.substring(0, 8) || 'new'}</span>
                <span className="message-count">{t.message_count ?? 0} msgs</span>
              </div>
            </div>
            <button 
              className="icon-btn sm thread-delete" 
              title="Delete" 
              onClick={(e) => { e.stopPropagation(); remove(t.thread_id); }}
            >
              <TrashIcon />
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
