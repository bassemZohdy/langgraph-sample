import { useEffect, useState } from 'react';
import { apiListThreads, type ThreadInfo } from '../lib/api';

type Props = {
  onSelect: (threadId: string) => void;
};

export function ThreadList({ onSelect }: Props) {
  const [threads, setThreads] = useState<ThreadInfo[]>([]);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const list = await apiListThreads();
      setThreads(list);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <section>
      <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>Threads</h3>
        <button onClick={load} disabled={loading}>{loading ? 'Refreshing...' : 'Refresh'}</button>
      </div>
      <div style={{ maxHeight: 200, overflow: 'auto', border: '1px solid var(--border)', borderRadius: 8, padding: 8 }}>
        {threads.length === 0 && <div className="muted">No threads yet.</div>}
        {threads.map((t) => (
          <div key={t.thread_id} style={{ padding: '6px 4px', cursor: 'pointer' }} onClick={() => onSelect(t.thread_id)}>
            <strong>{t.thread_id}</strong>
            <span className="muted"> • {t.message_count ?? 0} messages</span>
          </div>
        ))}
      </div>
    </section>
  );
}

