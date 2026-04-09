<template>
  <section class="history-layout">
    <article class="history-headline">
      <div>
        <p class="eyebrow">History</p>
        <h3>历史会话</h3>
        <p class="panel-copy">查看最近对话，点击任一会话即可返回工作台继续聊天。</p>
      </div>
      <button class="ghost-button" @click="store.fetchSessions">刷新列表</button>
    </article>

    <div class="history-list">
      <div v-if="store.sessions.length === 0" class="empty-state">
        还没有历史会话，先去首页发起第一轮提问吧。
      </div>
      <button
        v-for="session in store.sessions"
        :key="session.session_id"
        class="history-card"
        @click="openSession(session.session_id)"
      >
        <div>
          <h4>{{ session.title }}</h4>
          <p>{{ session.preview }}</p>
        </div>
        <span>{{ session.message_count }} 条消息</span>
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';

import { useChatStore } from '../stores/chat';

const router = useRouter();
const store = useChatStore();

onMounted(() => {
  if (store.sessions.length === 0) {
    store.fetchSessions();
  }
});

async function openSession(sessionId: string) {
  await store.loadSessionDetail(sessionId);
  router.push('/');
}
</script>
