
type Props = {
  value: string;
  setValue: (v: string) => void;
  sending?: boolean;
  onSend: () => void;
  onStop?: () => void;
  onRecallPrev?: () => void;
};

export function Composer({ value, setValue, sending, onSend, onStop, onRecallPrev }: Props) {
  return (
    <div className="composer">
      <textarea
        rows={3}
        placeholder="Type your message..."
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          // Enter sends; Shift+Enter for newline
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            onSend();
            return;
          }
          // Up arrow to recall previous message when caret at start
          if (e.key === 'ArrowUp') {
            const target = e.currentTarget;
            if (target.selectionStart === 0 && target.selectionEnd === 0) {
              onRecallPrev?.();
              e.preventDefault();
            }
          }
        }}
      />
      <div className="actions">
        {sending ? (
          <button className="danger" onClick={onStop}>Stop</button>
        ) : (
          <button onClick={onSend}>Send</button>
        )}
      </div>
    </div>
  );
}
