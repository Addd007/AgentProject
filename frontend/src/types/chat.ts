export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface SessionSummary {
  session_id: string;
  title: string;
  preview: string;
  message_count: number;
}

export interface SessionDetail {
  session_id: string;
  history: ChatMessage[];
}

export interface ChatResponse {
  reply: string;
  session_id: string;
}
