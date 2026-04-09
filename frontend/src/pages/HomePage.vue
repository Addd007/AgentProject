<template>
  <section class="workspace-grid">
    <SessionSidebar
      :sessions="store.sessions"
      :active-session-id="store.activeSessionId"
      :loading="store.isLoadingSessions"
      @create="createConversation"
      @select="handleSelect"
      @delete="store.deleteSession"
    />

    <div class="chat-stack">
      <ChatWindow :messages="store.activeMessages" :loading="store.isSending" />
      <MessageComposer :loading="store.isSending" @submit="store.sendMessage" @stop="store.stopGenerating" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';

import ChatWindow from '../components/home/ChatWindow.vue';
import MessageComposer from '../components/home/MessageComposer.vue';
import SessionSidebar from '../components/home/SessionSidebar.vue';
import { useChatStore } from '../stores/chat';

const store = useChatStore();

onMounted(async () => {
  await store.fetchSessions();
  if (store.activeSessionId) {
    try {
      await store.loadSessionDetail(store.activeSessionId);
    } catch {
      store.setActiveSession(null);
    }
  }
});

function handleSelect(sessionId: string) {
  store.loadSessionDetail(sessionId);
}

function createConversation() {
  store.createSession();
}
</script>
