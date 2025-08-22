
type Props = {
  threadId: string;
  setThreadId: (id: string) => void;
  onLoad: () => void;
  onNew: () => void;
  onDelete: () => void;
};

export function ThreadControls({ threadId, setThreadId, onLoad, onNew, onDelete }: Props) {
  return (
    <section className="thread-controls">
      <div className="row">
        <label>
          Thread ID
          <input
            type="text"
            placeholder="leave empty for new thread"
            value={threadId}
            onChange={(e) => setThreadId(e.target.value)}
          />
        </label>
        <button onClick={onLoad}>Load Messages</button>
        <button onClick={onNew}>New Thread</button>
        <button className="danger" onClick={onDelete}>Delete Thread</button>
      </div>
    </section>
  );
}
