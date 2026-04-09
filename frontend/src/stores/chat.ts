import { computed, ref } from 'vue';
import { defineStore } from 'pinia';

import { API_ENDPOINTS } from '../constants/api';
import { clearSessionCache, loadSessionCache, saveSessionCache } from '../utils/cache';
import type { ChatMessage, ChatResponse, SessionSummary } from '../types/chat';

const initialCache = loadSessionCache();

export const useChatStore = defineStore('chat', () => {
  const sessions = ref<SessionSummary[]>(initialCache.sessions);
  const messagesBySession = ref<Record<string, ChatMessage[]>>(initialCache.messagesBySession);
  const activeSessionId = ref<string | null>(initialCache.activeSessionId);
  const isSending = ref(false);
  const isLoadingSessions = ref(false);
  const activeSource = ref<EventSource | null>(null);
  const streamingSessionId = ref<string | null>(null);
  const streamingAssistantContent = ref('');
  const stopRequested = ref(false);

  const activeMessages = computed(() => {
    if (!activeSessionId.value) {
      return [];
    }
    return messagesBySession.value[activeSessionId.value] ?? [];
  });

  function persist() {
    saveSessionCache({
      activeSessionId: activeSessionId.value,
      sessions: sessions.value,
      messagesBySession: messagesBySession.value,
      updatedAt: Date.now(),
    });
  }

  function setActiveSession(sessionId: string | null) {
    activeSessionId.value = sessionId;
    persist();
  }

  function ensureSession(summary: SessionSummary) {
    const existingIndex = sessions.value.findIndex((item) => item.session_id === summary.session_id);
    if (existingIndex >= 0) {
      sessions.value[existingIndex] = summary;
    } else {
      sessions.value.unshift(summary);
    }
  }

  function updateSessionSummary(sessionId: string, messages: ChatMessage[]) {
    if (!messages?.length) {
      return;
    }

    const firstUserMessage = messages.find((item) => item.role === 'user')?.content ?? '新会话';
    ensureSession({
      session_id: sessionId,
      title: firstUserMessage.slice(0, 24) || '新会话',
      preview: '',
      message_count: messages.length,
    });
  }

  async function fetchSessions() {
    isLoadingSessions.value = true;
    try {
      const res = await fetch(API_ENDPOINTS.sessions, { credentials: 'include' });
      if (res.status === 401) {
        clearSessionCache();
        sessions.value = [];
        messagesBySession.value = {};
        activeSessionId.value = null;
        persist();
        return;
      }
      const data = await res.json() as { sessions: SessionSummary[] };
      sessions.value = data.sessions;
      if (!activeSessionId.value && sessions.value.length > 0) {
        activeSessionId.value = sessions.value[0].session_id;
      } else if (
        activeSessionId.value &&
        !activeSessionId.value.startsWith('local-') &&
        !sessions.value.some((item) => item.session_id === activeSessionId.value)
      ) {
        activeSessionId.value = sessions.value[0]?.session_id ?? null;
      }
      persist();
    } finally {
      isLoadingSessions.value = false;
    }
  }

  async function loadSessionDetail(sessionId: string) {
    if (!sessionId) {
      return;
    }

    if (sessionId.startsWith('local-')) {
      if (messagesBySession.value[sessionId]) {
        activeSessionId.value = sessionId;
        updateSessionSummary(sessionId, messagesBySession.value[sessionId]);
        persist();
      }
      return;
    }

    if (!sessions.value.some((item) => item.session_id === sessionId)) {
      activeSessionId.value = sessions.value[0]?.session_id ?? null;
      persist();
      return;
    }

    const res = await fetch(API_ENDPOINTS.session(sessionId), { credentials: 'include' });
    if (!res.ok) {
      if (res.status === 404) {
        sessions.value = sessions.value.filter((item) => item.session_id !== sessionId);
        delete messagesBySession.value[sessionId];
        if (activeSessionId.value === sessionId) {
          activeSessionId.value = sessions.value[0]?.session_id ?? null;
        }
        persist();
        return;
      }
      const errorText = await res.text();
      throw new Error(errorText || '加载会话失败');
    }

    const data = await res.json() as { session_id: string; history: ChatMessage[] };
    messagesBySession.value[sessionId] = data.history;
    activeSessionId.value = data.session_id;
    updateSessionSummary(sessionId, data.history);
    persist();
  }

  async function createSession() {
    activeSessionId.value = null;
    persist();
  }

  function finalizeStreamingState(source?: EventSource) {
    if (!source || activeSource.value === source) {
      activeSource.value = null;
    }
    streamingSessionId.value = null;
    streamingAssistantContent.value = '';
    stopRequested.value = false;
    isSending.value = false;
  }

  function stopGenerating() {
    if (!isSending.value) {
      return;
    }

    stopRequested.value = true;
    const sessionId = streamingSessionId.value;
    if (sessionId) {
      const sessionMessages = [...(messagesBySession.value[sessionId] ?? [])];
      if (sessionMessages.length > 0) {
        const assistantIndex = sessionMessages.length - 1;
        const content = streamingAssistantContent.value.trim() || '已停止生成';
        sessionMessages[assistantIndex] = { role: 'assistant', content };
        messagesBySession.value[sessionId] = sessionMessages;
        updateSessionSummary(sessionId, sessionMessages);
        persist();
      }
    }

    if (activeSource.value && activeSource.value.readyState !== EventSource.CLOSED) {
      activeSource.value.close();
    }
    finalizeStreamingState();
  }

  async function sendMessage(message: string) {
    const content = message.trim();
    if (!content || isSending.value) {
      return;
    }

    isSending.value = true;
    const tempSessionId = activeSessionId.value ?? `local-${Date.now()}`;
    const currentMessages: ChatMessage[] = [...(messagesBySession.value[tempSessionId] ?? [])];
    currentMessages.push({ role: 'user', content });
    currentMessages.push({ role: 'assistant', content: '' });
    messagesBySession.value[tempSessionId] = currentMessages;
    activeSessionId.value = tempSessionId;
    updateSessionSummary(tempSessionId, currentMessages);
    persist();

    const url = new URL(API_ENDPOINTS.chatStream, window.location.origin);
    url.searchParams.append('message', content);
    if (activeSessionId.value && !activeSessionId.value.startsWith('local-')) {
      url.searchParams.append('session_id', activeSessionId.value);
    }

    let assistantContent = '';
    let finalSessionId = tempSessionId;

    const source = new EventSource(url.toString(), { withCredentials: true });
    activeSource.value = source;
    streamingSessionId.value = tempSessionId;
    streamingAssistantContent.value = '';
    stopRequested.value = false;

    const updateAssistantMessage = () => {
      const sessionMessages = messagesBySession.value[tempSessionId];
      if (!sessionMessages?.length) {
        return;
      }
      const assistantIndex = sessionMessages.length - 1;
      sessionMessages[assistantIndex] = { role: 'assistant', content: assistantContent };
      messagesBySession.value[tempSessionId] = [...sessionMessages];
      streamingAssistantContent.value = assistantContent;
      persist();
    };

    const closeSource = () => {
      if (source.readyState !== EventSource.CLOSED) {
        source.close();
      }
    };

    return new Promise<void>((resolve) => {
      source.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as Record<string, unknown>;
          if (typeof data.chunk === 'string') {
            assistantContent += data.chunk;
            updateAssistantMessage();
          }
          if (data.done) {
            finalSessionId = typeof data.session_id === 'string' ? data.session_id : tempSessionId;
            closeSource();

            const sessionMessages = messagesBySession.value[tempSessionId] ?? [];
            if (tempSessionId !== finalSessionId) {
              delete messagesBySession.value[tempSessionId];
              messagesBySession.value[finalSessionId] = sessionMessages;
              sessions.value = sessions.value.filter((item) => item.session_id !== tempSessionId);
            }
            activeSessionId.value = finalSessionId;
            updateSessionSummary(finalSessionId, sessionMessages);
            persist();
            finalizeStreamingState(source);
            resolve();
          }
        } catch (error) {
          closeSource();
          const messageText = error instanceof Error ? error.message : '流式响应解析失败';
          const failedMsg: ChatMessage = { role: 'assistant', content: `请求失败：${messageText}` };
          const sessionMessages = [...(messagesBySession.value[tempSessionId] ?? [])];
          if (sessionMessages.length > 0) {
            sessionMessages[sessionMessages.length - 1] = failedMsg;
          } else {
            sessionMessages.push(failedMsg);
          }
          messagesBySession.value[tempSessionId] = sessionMessages;
          updateSessionSummary(tempSessionId, sessionMessages);
          persist();
          finalizeStreamingState(source);
          resolve();
        }
      };

      source.onerror = () => {
        if (stopRequested.value) {
          finalizeStreamingState(source);
          resolve();
          return;
        }
        closeSource();
        const failedMessages: ChatMessage[] = [...(messagesBySession.value[tempSessionId] ?? [])];
        if (failedMessages.length > 0) {
          failedMessages[failedMessages.length - 1] = { role: 'assistant', content: '请求失败：流式连接中断，请稍后重试。' };
        }
        messagesBySession.value[tempSessionId] = failedMessages;
        updateSessionSummary(tempSessionId, failedMessages);
        persist();
        finalizeStreamingState(source);
        resolve();
      };
    });
  }

  async function deleteSession(sessionId: string) {
    await fetch(API_ENDPOINTS.session(sessionId), { method: 'DELETE', credentials: 'include' });
    delete messagesBySession.value[sessionId];
    sessions.value = sessions.value.filter((item) => item.session_id !== sessionId);
    if (activeSessionId.value === sessionId) {
      activeSessionId.value = sessions.value[0]?.session_id ?? null;
    }
    persist();
  }

  return {
    sessions,
    activeSessionId,
    activeMessages,
    isSending,
    isLoadingSessions,
    createSession,
    fetchSessions,
    loadSessionDetail,
    setActiveSession,
    sendMessage,
    stopGenerating,
    deleteSession,
  };
});
