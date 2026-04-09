<template>
  <form class="composer" @submit.prevent="handleSubmit">
    <label class="composer-label" for="message">输入你的问题</label>
    <textarea
      id="message"
      v-model="draft"
      class="composer-input"
      placeholder="发消息给智能客服..."
      rows="2"
      :disabled="loading"
      @keydown="handleKeydown"
    />
    <div class="composer-actions">
      <p class="tiny-tip">Enter 发送，Shift + Enter 换行</p>
      <button
        class="send-button send-button--composer"
        :type="loading ? 'button' : 'submit'"
        :disabled="!loading && !draft.trim()"
        @click="loading ? emit('stop') : undefined"
      >
        {{ loading ? '停止' : '发送' }}
      </button>
    </div>
  </form>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const draft = ref('');

const props = defineProps<{
  loading: boolean;
}>();

const emit = defineEmits<{
  submit: [message: string];
  stop: [];
}>();

function handleSubmit() {
  const message = draft.value.trim();
  if (!message || props.loading) {
    return;
  }
  emit('submit', message);
  draft.value = '';
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key !== 'Enter') {
    return;
  }

  if (event.shiftKey) {
    return;
  }

  event.preventDefault();
  handleSubmit();
}
</script>
