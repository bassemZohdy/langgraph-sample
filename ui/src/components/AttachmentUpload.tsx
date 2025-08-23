import { useRef, useState } from 'react';
import { AttachmentIcon, TrashIcon } from './Icons';
import { apiUploadDocument } from '../lib/api';

export interface Attachment {
  id: string;
  file: File;
  name: string;
  size: number;
  type: string;
  progress?: number;
  uploaded?: boolean;
  error?: string;
  document_id?: string; // Backend document ID after upload
  chunks_created?: number; // Number of searchable chunks created
}

type Props = {
  attachments: Attachment[];
  onAttachmentsChange: (attachments: Attachment[]) => void;
  disabled?: boolean;
  maxFiles?: number;
  maxSizeBytes?: number;
  acceptedTypes?: string[];
};

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function getFileIcon(type: string): string {
  if (type.startsWith('image/')) return '🖼️';
  if (type.startsWith('video/')) return '🎥';
  if (type.startsWith('audio/')) return '🎵';
  if (type.includes('pdf')) return '📄';
  if (type.includes('text/')) return '📝';
  if (type.includes('word') || type.includes('docx')) return '📄';
  if (type.includes('excel') || type.includes('spreadsheet')) return '📊';
  if (type.includes('powerpoint') || type.includes('presentation')) return '📈';
  if (type.includes('zip') || type.includes('rar') || type.includes('archive')) return '📦';
  return '📎';
}

export function AttachmentUpload({ 
  attachments, 
  onAttachmentsChange, 
  disabled = false,
  maxFiles = 5,
  maxSizeBytes = 10 * 1024 * 1024, // 10MB default
  acceptedTypes = [
    'image/*',
    'text/*', 
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  ]
}: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  function handleFileSelect(files: FileList | null) {
    if (!files || disabled) return;
    
    const newAttachments: Attachment[] = [];
    const existingCount = attachments.length;
    
    for (let i = 0; i < files.length && (existingCount + newAttachments.length) < maxFiles; i++) {
      const file = files[i];
      
      // Check file size
      if (file.size > maxSizeBytes) {
        // Could show error toast/notification here
        console.warn(`File ${file.name} is too large (${formatFileSize(file.size)} > ${formatFileSize(maxSizeBytes)})`);
        continue;
      }
      
      // Check file type (basic check)
      const accepted = acceptedTypes.some(type => {
        if (type.endsWith('/*')) {
          return file.type.startsWith(type.slice(0, -1));
        }
        return file.type === type;
      });
      
      if (!accepted) {
        console.warn(`File ${file.name} type ${file.type} is not accepted`);
        continue;
      }
      
      newAttachments.push({
        id: generateId(),
        file,
        name: file.name,
        size: file.size,
        type: file.type,
        progress: 0,
        uploaded: false
      });
    }
    
    if (newAttachments.length > 0) {
      const updatedAttachments = [...attachments, ...newAttachments];
      onAttachmentsChange(updatedAttachments);
      
      // Upload files automatically
      newAttachments.forEach(attachment => {
        uploadFile(attachment);
      });
    }
  }

  async function uploadFile(attachment: Attachment) {
    try {
      // Update progress to show upload starting
      updateAttachmentProgress(attachment.id, 10);
      
      // Upload to backend
      const response = await apiUploadDocument(attachment.file);
      
      // Update attachment with backend response
      updateAttachmentComplete(attachment.id, {
        document_id: response.document_id,
        chunks_created: response.chunks_created,
        uploaded: true,
        progress: 100
      });
      
      console.log(`File uploaded successfully: ${response.message}`);
      
    } catch (error) {
      console.error(`Failed to upload ${attachment.name}:`, error);
      updateAttachmentError(attachment.id, error instanceof Error ? error.message : 'Upload failed');
    }
  }

  function updateAttachmentProgress(id: string, progress: number) {
    onAttachmentsChange(attachments.map(a => 
      a.id === id ? { ...a, progress } : a
    ));
  }

  function updateAttachmentComplete(id: string, updates: Partial<Attachment>) {
    onAttachmentsChange(attachments.map(a => 
      a.id === id ? { ...a, ...updates } : a
    ));
  }

  function updateAttachmentError(id: string, error: string) {
    onAttachmentsChange(attachments.map(a => 
      a.id === id ? { ...a, error, progress: 0 } : a
    ));
  }

  function removeAttachment(id: string) {
    onAttachmentsChange(attachments.filter(a => a.id !== id));
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    handleFileSelect(e.dataTransfer.files);
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(true);
  }

  function handleDragLeave(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
  }

  function openFileDialog() {
    if (!disabled) {
      fileInputRef.current?.click();
    }
  }

  return (
    <div className="attachment-upload">
      {/* File Input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept={acceptedTypes.join(',')}
        style={{ display: 'none' }}
        onChange={(e) => handleFileSelect(e.target.files)}
        disabled={disabled}
      />
      
      {/* Upload Button */}
      <button
        type="button"
        className={`icon-btn attachment-btn ${attachments.length > 0 ? 'has-attachments' : ''}`}
        onClick={openFileDialog}
        disabled={disabled || attachments.length >= maxFiles}
        title={
          disabled ? "Upload disabled" :
          attachments.length >= maxFiles ? `Maximum ${maxFiles} files allowed` :
          `Add files for document search (${attachments.length}/${maxFiles})`
        }
      >
        <AttachmentIcon />
        {attachments.length > 0 && (
          <span className="attachment-count">{attachments.length}</span>
        )}
      </button>
      
      {/* Drop Zone (appears when dragging) */}
      {dragOver && (
        <div
          className="drop-zone"
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
        >
          <div className="drop-zone-content">
            <AttachmentIcon />
            <p>Drop files here</p>
          </div>
        </div>
      )}
      
      {/* Attachment List */}
      {attachments.length > 0 && (
        <div className="attachment-list">
          {attachments.map((attachment) => (
            <div key={attachment.id} className="attachment-item">
              <div className="attachment-info">
                <span className="attachment-icon">{getFileIcon(attachment.type)}</span>
                <div className="attachment-details">
                  <span className="attachment-name" title={attachment.name}>
                    {attachment.name}
                  </span>
                  <span className="attachment-size">{formatFileSize(attachment.size)}</span>
                </div>
                {attachment.progress !== undefined && attachment.progress < 100 && (
                  <div className="attachment-progress" title={`Uploading... ${attachment.progress}%`}>
                    <div 
                      className="attachment-progress-bar" 
                      style={{ width: `${attachment.progress}%` }}
                    />
                    <span className="progress-text">{attachment.progress}%</span>
                  </div>
                )}
                {attachment.uploaded && attachment.chunks_created && (
                  <span 
                    className="attachment-success" 
                    title={`Document uploaded and processed into ${attachment.chunks_created} searchable chunks`}
                  >
                    ✅ {attachment.chunks_created} chunks
                  </span>
                )}
                {attachment.error && (
                  <span className="attachment-error" title={attachment.error}>❌</span>
                )}
              </div>
              <button
                type="button"
                className="icon-btn sm attachment-remove"
                onClick={() => removeAttachment(attachment.id)}
                title="Remove attachment"
                disabled={disabled}
              >
                <TrashIcon />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}