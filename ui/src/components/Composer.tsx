
import { AttachmentUpload, type Attachment } from './AttachmentUpload';

type Props = {
  value: string;
  setValue: (v: string) => void;
  sending?: boolean;
  onSend: () => void;
  onStop?: () => void;
  onRecallPrev?: () => void;
  attachments?: Attachment[];
  onAttachmentsChange?: (attachments: Attachment[]) => void;
};

export function Composer({ 
  value, 
  setValue, 
  sending, 
  onSend, 
  onStop, 
  onRecallPrev, 
  attachments = [], 
  onAttachmentsChange 
}: Props) {
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
        {onAttachmentsChange && (
          <AttachmentUpload
            attachments={attachments}
            onAttachmentsChange={onAttachmentsChange}
            disabled={sending}
          />
        )}
        {sending ? (
          <button className="danger" onClick={onStop}>Stop</button>
        ) : (
          <button onClick={onSend}>Send</button>
        )}
      </div>
    </div>
  );
}
