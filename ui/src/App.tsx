import { useEffect, useRef, useState } from 'react';
import { apiChat, apiGetThreadMessages, apiHealth, apiGetModels } from './lib/api';
import type { ChatMessage } from './lib/types';
import { MessageList } from './components/MessageList';
import { Composer } from './components/Composer';
import { ThreadList } from './components/ThreadList';
import { SunIcon, MoonIcon, MonitorIcon, SidebarOpenIcon, SidebarClosedIcon } from './components/Icons';
import type { Attachment } from './components/AttachmentUpload';

function generateThreadId(): string {
  const arr = new Uint8Array(8);
  if (typeof crypto !== 'undefined' && (crypto as any).getRandomValues) {
    crypto.getRandomValues(arr);
  } else {
    for (let i = 0; i < arr.length; i++) arr[i] = Math.floor(Math.random() * 256);
  }
  return 'thread_' + Array.from(arr).map(b => b.toString(16).padStart(2, '0')).join('');
}

export default function App() {
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [threadId, setThreadId] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [lastUserMessage, setLastUserMessage] = useState('');
  const [threadsVersion, setThreadsVersion] = useState(0);
  const [currentModel, setCurrentModel] = useState<string>('');
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const [theme, setTheme] = useState<'light' | 'dark' | 'system'>(() => {
    const saved = localStorage.getItem('theme');
    if (saved === 'light' || saved === 'dark' || saved === 'system') return saved;
    return 'system';
  });

  // Get effective theme for components
  function getEffectiveTheme(): 'light' | 'dark' {
    if (theme === 'system') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return theme;
  }


  useEffect(() => {
    apiHealth().then((ok: boolean) => setApiOk(ok));
    // Load model information
    apiGetModels().then((modelInfo) => {
      if (modelInfo.primary_provider && modelInfo.providers[modelInfo.primary_provider]) {
        const provider = modelInfo.providers[modelInfo.primary_provider];
        setCurrentModel(`${modelInfo.primary_provider}:${provider.model}`);
      }
    }).catch(() => {
      setCurrentModel('Unknown');
    });
  }, []);

  // Apply theme and track system preference when in "system" mode
  useEffect(() => {
    const mql = window.matchMedia('(prefers-color-scheme: dark)');
    function apply(mode: 'light' | 'dark' | 'system') {
      const effective = mode === 'system' ? (mql.matches ? 'dark' : 'light') : mode;
      document.documentElement.setAttribute('data-theme', effective);
    }
    apply(theme);
    localStorage.setItem('theme', theme);
    function onChange() {
      if (theme === 'system') apply('system');
    }
    mql.addEventListener?.('change', onChange);
    return () => mql.removeEventListener?.('change', onChange);
  }, [theme]);

  async function loadThread() {
    if (!threadId) return alert('Enter a thread ID');
    try {
      const msgs = await apiGetThreadMessages(threadId);
      setMessages(msgs);
    } catch (e: any) {
      alert(e?.message || 'Failed to load thread');
    }
  }

  function newThread() {
    setThreadId(generateThreadId());
    setMessages([]);
    setAttachments([]);
  }

  // delete handled directly in ThreadList

  async function send() {
    if (!input.trim()) return;
    const text = input.trim();
    // Optimistically add user message and a pending assistant placeholder
    setMessages(prev => [
      ...prev,
      { role: 'user', content: text },
      { role: 'assistant', content: '', pending: true } as any,
    ]);
    setInput('');
    setLastUserMessage(text);
    setSending(true);
    try {
      // Abort any previous in-flight request
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      const res = await apiChat(text, threadId || undefined, { signal: controller.signal });
      if (!threadId) setThreadId(res.thread_id);

      // Take only the latest assistant message from server
      let assistantContent = '';
      const serverMsgs = res.messages || [];
      if (serverMsgs.length) {
        const last = serverMsgs[serverMsgs.length - 1];
        assistantContent = last?.content ?? '';
      }

      setMessages(prev => {
        const copy = [...prev];
        for (let i = copy.length - 1; i >= 0; i--) {
          if ((copy[i] as any).pending) {
            copy[i] = { role: 'assistant', content: assistantContent } as ChatMessage;
            return copy;
          }
        }
        return [...copy, { role: 'assistant', content: assistantContent } as ChatMessage];
      });
      // Thread messages have changed; refresh list
      setThreadsVersion(v => v + 1);
    } catch (e: any) {
      setMessages(prev => {
        const copy = [...prev];
        for (let i = copy.length - 1; i >= 0; i--) {
          if ((copy[i] as any).pending) {
            const aborted = e?.name === 'AbortError';
            copy[i] = { role: 'assistant', content: aborted ? 'Stopped.' : (e?.message || 'Failed to send message') } as ChatMessage;
            return copy;
          }
        }
        const aborted = e?.name === 'AbortError';
        return [...copy, { role: 'assistant', content: aborted ? 'Stopped.' : (e?.message || 'Failed to send message') } as ChatMessage];
      });
    } finally {
      setSending(false);
      abortRef.current = null;
    }
  }

  function stop() {
    abortRef.current?.abort();
  }

  return (
    <div>
      <header>
        <div className="header-content">
          <div className="title-section">
            <h1>LangGraph Agent</h1>
            <div className="model-info">
              <span className="model-label">Model:</span>
              <span className="model-name">{currentModel || 'Loading...'}</span>
            </div>
          </div>
          <div className="settings toolbar">
            <div className="health-status">
              <span 
                className={`health-icon ${apiOk === null ? 'loading' : apiOk ? 'healthy' : 'error'}`}
                title={apiOk === null ? 'Checking health...' : apiOk ? 'API Healthy' : 'API Unavailable'}
              >
                ●
              </span>
              <span className="health-text">{apiOk === null ? 'Checking...' : apiOk ? 'Healthy' : 'Unavailable'}</span>
            </div>
            <button className="icon-btn" title={sidebarOpen ? 'Hide threads' : 'Show threads'} onClick={() => setSidebarOpen(v => !v)}>
              {sidebarOpen ? <SidebarOpenIcon /> : <SidebarClosedIcon />}
            </button>
            <button
              className="icon-btn"
              title={`Theme: ${theme}`}
              onClick={() => setTheme(theme === 'system' ? 'light' : theme === 'light' ? 'dark' : 'system')}
            >
              {theme === 'system' ? <MonitorIcon /> : theme === 'light' ? <SunIcon /> : <MoonIcon />}
            </button>
          </div>
        </div>
      </header>

      <div className={`layout ${sidebarOpen ? '' : 'no-sidebar'}`}>
        <aside className="sidebar">
          <ThreadList
            onSelect={(id) => { setThreadId(id); loadThread(); }}
            onNewThread={newThread}
            version={threadsVersion}
            onChanged={() => setThreadsVersion(v => v + 1)}
            selectedThreadId={threadId}
          />
        </aside>

        <section className="chat">
          <MessageList messages={messages} theme={getEffectiveTheme()} />
          <Composer
            value={input}
            setValue={setInput}
            sending={sending}
            onSend={send}
            onStop={stop}
            onRecallPrev={() => setInput(lastUserMessage)}
            attachments={attachments}
            onAttachmentsChange={setAttachments}
          />
        </section>
      </div>
    </div>
  );
}
