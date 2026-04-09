<template>
  <section class="auth-page">
    <div class="auth-card">
      <div class="auth-copy">
        <p class="eyebrow">AgentProject</p>
        <h1>登录智能客服工作台</h1>
        <p class="panel-copy">注册后可安全保存聊天记录，并在下次访问时继续之前的会话。</p>
      </div>

      <div class="auth-tabs">
        <button
          class="auth-tab"
          :class="{ 'auth-tab--active': mode === 'login' }"
          type="button"
          @click="mode = 'login'"
        >
          登录
        </button>
        <button
          class="auth-tab"
          :class="{ 'auth-tab--active': mode === 'register' }"
          type="button"
          @click="mode = 'register'"
        >
          注册
        </button>
      </div>

      <form class="auth-form" @submit.prevent="handleSubmit">
        <label class="auth-label" for="username">用户名</label>
        <input id="username" v-model.trim="username" class="auth-input" autocomplete="username" />

        <label class="auth-label" for="password">密码</label>
        <input
          id="password"
          v-model="password"
          type="password"
          class="auth-input"
          autocomplete="current-password"
        />

        <p v-if="errorMessage" class="auth-error">{{ errorMessage }}</p>

        <button class="send-button auth-submit" type="submit" :disabled="authStore.isSubmitting">
          {{ authStore.isSubmitting ? '提交中...' : mode === 'login' ? '登录' : '注册并登录' }}
        </button>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';

import { useAuthStore } from '../stores/auth';

const router = useRouter();
const authStore = useAuthStore();

const mode = ref<'login' | 'register'>('login');
const username = ref('');
const password = ref('');
const errorMessage = ref('');

async function handleSubmit() {
  errorMessage.value = '';
  const normalizedUsername = username.value.trim();

  if (normalizedUsername.length < 3 || normalizedUsername.length > 32) {
    errorMessage.value = '用户名长度需在 3 到 32 位之间';
    return;
  }

  if (password.value.length < 8 || password.value.length > 128) {
    errorMessage.value = '密码长度需在 8 到 128 位之间';
    return;
  }

  try {
    if (mode.value === 'login') {
      await authStore.login(normalizedUsername, password.value);
    } else {
      await authStore.register(normalizedUsername, password.value);
    }
    await router.replace('/');
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '提交失败';
  }
}
</script>