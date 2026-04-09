<template>
  <section class="session-sidebar">
    <div class="session-sidebar__header">
      <div>
        <p class="eyebrow">Sessions</p>
        <h3>最近会话</h3>
      </div>
      <div class="session-toolbar">
        <button class="send-button" @click="$emit('create')">新建</button>
      </div>
    </div>

    <div class="session-list">
      <div v-if="loading" class="tiny-tip">正在同步服务端会话...</div>
      <div v-else-if="sessions.length === 0" class="empty-state compact">
        暂无会话，点击上方“新建”开始提问。
      </div>

      <button
        v-for="session in sessions"
        :key="session.session_id"
        class="session-item"
        :class="{ 'session-item--active': activeSessionId === session.session_id }"
        @click="$emit('select', session.session_id)"
      >
        <div class="session-item__body">
          <strong>{{ session.title }}</strong>
        </div>
        <div class="session-item__meta">
          <span>{{ session.message_count }} 条</span>
          <span class="session-delete" @click.stop="$emit('delete', session.session_id)">删除</span>
        </div>
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { SessionSummary } from '../../types/chat';

defineProps<{
  sessions: SessionSummary[];
  activeSessionId: string | null;
  loading: boolean;
}>();

defineEmits<{
  create: [];
  select: [sessionId: string];
  delete: [sessionId: string];
}>();
</script>
