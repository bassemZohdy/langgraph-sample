import { useEffect, useState } from 'react';
import { apiDeleteThread, apiListThreads, type ThreadInfo } from '../lib/api';
import { PlusIcon, TrashIcon } from './Icons';

type Props = {
  onSelect: (threadId: string) => void;
  onNewThread?: () => void;
  version?: number; // when this changes, refresh list
  onChanged?: () => void; // notify parent to refresh elsewhere
};

export function ThreadList({ onSelect, onNewThread, version = 0, onChanged }: Props) {
  const [threads, setThreads] = useState<ThreadInfo[]>([]);

  async function load() {
    const list = await apiListThreads();
    setThreads(list);
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
      <div style={{ maxHeight: 240, overflow: 'auto', border: '1px solid var(--border)', borderRadius: 8, padding: 8 }}>
        {threads.length === 0 && <div className="muted">No threads yet.</div>}
        {threads.map((t) => (
          <div key={t.thread_id} className="thread-item" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, padding: '6px 4px' }}>
            <div style={{ cursor: 'pointer', overflow: 'hidden', textOverflow: 'ellipsis' }} onClick={() => onSelect(t.thread_id)}>
              <strong>{t.thread_id}</strong>
              <span className="muted"> • {t.message_count ?? 0}</span>
            </div>
            <button className="icon-btn" title="Delete" onClick={(e) => { e.stopPropagation(); remove(t.thread_id); }}>
              <TrashIcon />
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
