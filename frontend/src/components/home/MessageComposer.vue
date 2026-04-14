<template>
  <form class="composer" @submit.prevent="handleSubmit">
    <label class="composer-label" for="message">输入你的问题</label>
    <textarea
      ref="textareaRef"
      id="message"
      v-model="draft"
      class="composer-input"
      placeholder="发消息给智能客服..."
      rows="2"
      :disabled="loading"
      @input="syncComposerHeight"
      @keydown="handleKeydown"
    />
    <div class="composer-actions">
      <p class="tiny-tip composer-tip">Cmd/Ctrl + Enter 发送，Enter 换行</p>
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
import { nextTick, onMounted, ref } from 'vue';

const draft = ref('');
const textareaRef = ref<HTMLTextAreaElement | null>(null);

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
  nextTick(syncComposerHeight);
}

function syncComposerHeight() {
  const textarea = textareaRef.value;
  if (!textarea) {
    return;
  }

  textarea.style.height = 'auto';
  textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`;
  textarea.style.overflowY = textarea.scrollHeight > 180 ? 'auto' : 'hidden';
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key !== 'Enter' || event.isComposing) {
    return;
  }

  if (!event.metaKey && !event.ctrlKey) {
    return;
  }

  event.preventDefault();
  handleSubmit();
}

onMounted(syncComposerHeight);
</script>
