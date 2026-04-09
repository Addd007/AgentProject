<template>
  <section class="chat-window">
    <div class="chat-window__header">
      <div>
        <p class="eyebrow">Conversation</p>
        <h3>当前对话</h3>
      </div>
      <div class="chat-window__meta">
        <div class="chat-window__actions">
          <span class="chat-window__user">{{ authStore.user?.username }}</span>
          <button class="ghost-button" type="button" @click="handleLogout">退出登录</button>
        </div>
        <span class="tiny-tip">{{ loading ? '正在生成回复...' : '响应已完成' }}</span>
      </div>
    </div>

    <div v-if="messages.length === 0" class="empty-state empty-state--chat">
      <h3>今天想解决什么问题？</h3>
      <p>从左侧选择会话，或直接在下方输入问题开始新的对话。</p>
    </div>

    <div v-else class="message-list">
      <article
        v-for="(message, index) in messages"
        :key="`${message.role}-${index}`"
        class="message-bubble"
        :class="`message-bubble--${message.role}`"
      >
        <div class="message-bubble__avatar">{{ message.role === 'user' ? '你' : 'AI' }}</div>
        <div class="message-bubble__content">
          <header>{{ message.role === 'user' ? '你' : '智能客服' }}</header>
          <p>{{ message.content }}</p>
        </div>
      </article>
      <div ref="bottomAnchor"></div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue';
import { useRouter } from 'vue-router';

import type { ChatMessage } from '../../types/chat';
import { useAuthStore } from '../../stores/auth';

const props = defineProps<{
  messages: ChatMessage[];
  loading: boolean;
}>();

const router = useRouter();
const authStore = useAuthStore();
const bottomAnchor = ref<HTMLDivElement | null>(null);

async function scrollToBottom() {
  await nextTick();
  bottomAnchor.value?.scrollIntoView({ behavior: 'smooth', block: 'end' });
}

async function handleLogout() {
  await authStore.logout();
  await router.replace('/auth');
}

watch(
  () => [props.messages.length, props.loading],
  () => {
    void scrollToBottom();
  },
  { flush: 'post' },
);
</script>
