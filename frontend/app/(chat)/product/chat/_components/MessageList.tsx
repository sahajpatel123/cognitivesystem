import { useRef, useEffect } from "react";
import { MessageBubble } from "./MessageBubble";
import { Action } from "../contract_runtime";

type Message = {
  id: string;
  role: "user" | "system";
  text: string;
  action?: Action;
  failureType?: string | null;
};

type MessageListProps = {
  messages: Message[];
  isSending: boolean;
  isClosed: boolean;
  onCopyMessage: (text: string) => void;
};

export function MessageList({ messages, isSending, isClosed, onCopyMessage }: MessageListProps) {
  const listRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="message-list" ref={listRef}>
      {messages.length === 0 && (
        <div className="message-list-empty">
          <p>Send a message to begin your governed conversation.</p>
        </div>
      )}
      {messages.map((msg) => (
        <MessageBubble
          key={msg.id}
          id={msg.id}
          role={msg.role}
          text={msg.text}
          action={msg.action}
          failureType={msg.failureType}
          onCopy={onCopyMessage}
        />
      ))}
      {isSending && (
        <div className="message-thinking">
          <span className="thinking-dots">
            <span></span>
            <span></span>
            <span></span>
          </span>
          <span className="thinking-text">Generating response...</span>
        </div>
      )}
      {isClosed && (
        <div className="message-closed-notice">
          Conversation closed by governance rules.
        </div>
      )}
    </div>
  );
}
