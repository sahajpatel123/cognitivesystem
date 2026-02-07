import { FormEvent, KeyboardEvent, useRef, useEffect, useState } from "react";

type Attachment = {
  id: string;
  kind: "image" | "file";
  file: File;
  previewUrl?: string;
  name: string;
  size: number;
  mime: string;
};

type ChatComposerProps = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled: boolean;
  isSending: boolean;
  onFocus?: () => void;
  onBlur?: () => void;
  attachments?: Attachment[];
  onAttachmentsChange?: (attachments: Attachment[]) => void;
};

export function ChatComposer({ value, onChange, onSubmit, disabled, isSending, onFocus, onBlur, attachments = [], onAttachmentsChange }: ChatComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const [isAttachOpen, setIsAttachOpen] = useState(false);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      const scrollHeight = textareaRef.current.scrollHeight;
      const maxHeight = 24 * 5;
      textareaRef.current.style.height = `${Math.min(scrollHeight, maxHeight)}px`;
    }
  }, [value]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setIsAttachOpen(false);
      }
    };
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsAttachOpen(false);
      }
    };
    if (isAttachOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleEscape as any);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape as any);
    };
  }, [isAttachOpen]);

  useEffect(() => {
    return () => {
      attachments.forEach((att) => {
        if (att.previewUrl) {
          URL.revokeObjectURL(att.previewUrl);
        }
      });
    };
  }, []);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!disabled && value.trim() && !isSending) {
      onSubmit();
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!disabled && value.trim() && !isSending) {
        onSubmit();
      }
    }
  };

  const handleAttachClick = () => {
    setIsAttachOpen(!isAttachOpen);
  };

  const handleImageUpload = () => {
    imageInputRef.current?.click();
    setIsAttachOpen(false);
  };

  const handleFileUpload = () => {
    fileInputRef.current?.click();
    setIsAttachOpen(false);
  };

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    addAttachments(files, "image");
    e.target.value = "";
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    addAttachments(files, "file");
    e.target.value = "";
  };

  const addAttachments = (files: File[], kind: "image" | "file") => {
    if (!onAttachmentsChange) return;
    const MAX_ATTACHMENTS = 10;
    const remaining = MAX_ATTACHMENTS - attachments.length;
    if (remaining <= 0) {
      alert(`Maximum ${MAX_ATTACHMENTS} attachments allowed`);
      return;
    }
    const filesToAdd = files.slice(0, remaining);
    const newAttachments: Attachment[] = filesToAdd.map((file) => ({
      id: crypto.randomUUID(),
      kind,
      file,
      previewUrl: kind === "image" ? URL.createObjectURL(file) : undefined,
      name: file.name,
      size: file.size,
      mime: file.type,
    }));
    onAttachmentsChange([...attachments, ...newAttachments]);
  };

  const removeAttachment = (id: string) => {
    if (!onAttachmentsChange) return;
    const att = attachments.find((a) => a.id === id);
    if (att?.previewUrl) {
      URL.revokeObjectURL(att.previewUrl);
    }
    onAttachmentsChange(attachments.filter((a) => a.id !== id));
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  const sendDisabled = disabled || !value.trim() || isSending;

  return (
    <div className="chat-composer-wrapper">
      {attachments.length > 0 && (
        <div className="attachment-tray">
          {attachments.map((att) => (
            <div key={att.id} className="attachment-item">
              {att.kind === "image" && att.previewUrl ? (
                <div className="attachment-image">
                  <img src={att.previewUrl} alt={att.name} />
                  <button
                    type="button"
                    className="attachment-remove"
                    onClick={() => removeAttachment(att.id)}
                    aria-label="Remove attachment"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  </button>
                </div>
              ) : (
                <div className="attachment-file">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
                    <polyline points="13 2 13 9 20 9" />
                  </svg>
                  <div className="attachment-file-info">
                    <div className="attachment-file-name">{att.name}</div>
                    <div className="attachment-file-size">{formatFileSize(att.size)}</div>
                  </div>
                  <button
                    type="button"
                    className="attachment-remove"
                    onClick={() => removeAttachment(att.id)}
                    aria-label="Remove attachment"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
      <form className="chat-composer" onSubmit={handleSubmit}>
        <div className="chat-composer-attach-wrapper" ref={popoverRef}>
          <button
            type="button"
            className="chat-composer-attach"
            disabled={disabled}
            onClick={handleAttachClick}
            aria-label="Add attachments"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
          </button>
          {isAttachOpen && (
            <div className="attach-popover">
              <button type="button" className="attach-option" onClick={handleImageUpload}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <polyline points="21 15 16 10 5 21" />
                </svg>
                <span>Upload image</span>
              </button>
              <button type="button" className="attach-option" onClick={handleFileUpload}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
                  <polyline points="13 2 13 9 20 9" />
                </svg>
                <span>Upload file</span>
              </button>
            </div>
          )}
          <input
            ref={imageInputRef}
            type="file"
            accept="image/*"
            multiple
            onChange={handleImageChange}
            style={{ display: "none" }}
          />
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt,.md,.doc,.docx,.ppt,.pptx,.csv,.json,*/*"
            multiple
            onChange={handleFileChange}
            style={{ display: "none" }}
          />
        </div>
        <textarea
          ref={textareaRef}
          className="chat-composer-input"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={onFocus}
          onBlur={onBlur}
          placeholder={disabled ? "Chat closed" : "Message Cognitive System..."}
          disabled={disabled}
          rows={1}
        />
        <button
          type="submit"
          className="chat-composer-send"
          disabled={sendDisabled}
          aria-label="Send message"
        >
          {isSending ? (
            <svg className="chat-composer-spinner" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" opacity="0.25" />
              <path d="M12 2a10 10 0 0 1 10 10" opacity="0.75" />
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          )}
        </button>
      </form>
      <div className="chat-composer-footer">
        Verify independently. Not medical, legal, or financial advice.
      </div>
    </div>
  );
}
