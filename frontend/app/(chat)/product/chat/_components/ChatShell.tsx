import { ReactNode } from "react";

type ChatShellProps = {
  children: ReactNode;
};

export function ChatShell({ children }: ChatShellProps) {
  return (
    <div className="chat-shell-container">
      <div className="chat-shell-card">
        {children}
      </div>
    </div>
  );
}
