import { nextTick, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../../stores/auth';
const props = defineProps();
const router = useRouter();
const authStore = useAuthStore();
const bottomAnchor = ref(null);
async function scrollToBottom() {
    await nextTick();
    bottomAnchor.value?.scrollIntoView({ behavior: 'smooth', block: 'end' });
}
async function handleLogout() {
    await authStore.logout();
    await router.replace('/auth');
}
watch(() => [props.messages.length, props.loading], () => {
    void scrollToBottom();
}, { flush: 'post' });
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.section, __VLS_intrinsicElements.section)({
    ...{ class: "chat-window" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "chat-window__header" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
    ...{ class: "eyebrow" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.h3, __VLS_intrinsicElements.h3)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "chat-window__meta" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "chat-window__actions" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "chat-window__user" },
});
(__VLS_ctx.authStore.user?.username);
__VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
    ...{ onClick: (__VLS_ctx.handleLogout) },
    ...{ class: "ghost-button" },
    type: "button",
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "tiny-tip" },
});
(__VLS_ctx.loading ? '正在生成回复...' : '响应已完成');
if (__VLS_ctx.messages.length === 0) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "empty-state empty-state--chat" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.h3, __VLS_intrinsicElements.h3)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({});
}
else {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "message-list" },
    });
    for (const [message, index] of __VLS_getVForSourceType((__VLS_ctx.messages))) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.article, __VLS_intrinsicElements.article)({
            key: (`${message.role}-${index}`),
            ...{ class: "message-bubble" },
            ...{ class: (`message-bubble--${message.role}`) },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "message-bubble__avatar" },
        });
        (message.role === 'user' ? '你' : 'AI');
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "message-bubble__content" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.header, __VLS_intrinsicElements.header)({});
        (message.role === 'user' ? '你' : '智能客服');
        __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({});
        (message.content);
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ref: "bottomAnchor",
    });
    /** @type {typeof __VLS_ctx.bottomAnchor} */ ;
}
/** @type {__VLS_StyleScopedClasses['chat-window']} */ ;
/** @type {__VLS_StyleScopedClasses['chat-window__header']} */ ;
/** @type {__VLS_StyleScopedClasses['eyebrow']} */ ;
/** @type {__VLS_StyleScopedClasses['chat-window__meta']} */ ;
/** @type {__VLS_StyleScopedClasses['chat-window__actions']} */ ;
/** @type {__VLS_StyleScopedClasses['chat-window__user']} */ ;
/** @type {__VLS_StyleScopedClasses['ghost-button']} */ ;
/** @type {__VLS_StyleScopedClasses['tiny-tip']} */ ;
/** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
/** @type {__VLS_StyleScopedClasses['empty-state--chat']} */ ;
/** @type {__VLS_StyleScopedClasses['message-list']} */ ;
/** @type {__VLS_StyleScopedClasses['message-bubble']} */ ;
/** @type {__VLS_StyleScopedClasses['message-bubble__avatar']} */ ;
/** @type {__VLS_StyleScopedClasses['message-bubble__content']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            authStore: authStore,
            bottomAnchor: bottomAnchor,
            handleLogout: handleLogout,
        };
    },
    __typeProps: {},
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    __typeProps: {},
});
; /* PartiallyEnd: #4569/main.vue */
