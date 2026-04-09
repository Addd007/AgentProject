import type { ChatMessage, SessionSummary } from '../types/chat';

export interface LocalSessionCache {
  activeSessionId: string | null;
  sessions: SessionSummary[];
  messagesBySession: Record<string, ChatMessage[]>;
  updatedAt: number;
}
