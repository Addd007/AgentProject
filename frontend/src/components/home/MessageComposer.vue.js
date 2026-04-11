/// <reference types="../../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { ref } from 'vue';
const draft = ref('');
const props = defineProps();
const emit = defineEmits();
function handleSubmit() {
    const message = draft.value.trim();
    if (!message || props.loading) {
        return;
    }
    emit('submit', message);
    draft.value = '';
}
function handleKeydown(event) {
    if (event.key !== 'Enter') {
        return;
    }
    if (event.shiftKey) {
        return;
    }
    event.preventDefault();
    handleSubmit();
}
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.form, __VLS_intrinsicElements.form)({
    ...{ onSubmit: (__VLS_ctx.handleSubmit) },
    ...{ class: "composer" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({
    ...{ class: "composer-label" },
    for: "message",
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.textarea)({
    ...{ onKeydown: (__VLS_ctx.handleKeydown) },
    id: "message",
    value: (__VLS_ctx.draft),
    ...{ class: "composer-input" },
    placeholder: "发消息给智能客服...",
    rows: "2",
    disabled: (__VLS_ctx.loading),
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "composer-actions" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
    ...{ class: "tiny-tip" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.loading ? __VLS_ctx.emit('stop') : undefined;
        } },
    ...{ class: "send-button send-button--composer" },
    type: (__VLS_ctx.loading ? 'button' : 'submit'),
    disabled: (!__VLS_ctx.loading && !__VLS_ctx.draft.trim()),
});
(__VLS_ctx.loading ? '停止' : '发送');
/** @type {__VLS_StyleScopedClasses['composer']} */ ;
/** @type {__VLS_StyleScopedClasses['composer-label']} */ ;
/** @type {__VLS_StyleScopedClasses['composer-input']} */ ;
/** @type {__VLS_StyleScopedClasses['composer-actions']} */ ;
/** @type {__VLS_StyleScopedClasses['tiny-tip']} */ ;
/** @type {__VLS_StyleScopedClasses['send-button']} */ ;
/** @type {__VLS_StyleScopedClasses['send-button--composer']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            draft: draft,
            emit: emit,
            handleSubmit: handleSubmit,
            handleKeydown: handleKeydown,
        };
    },
    __typeEmits: {},
    __typeProps: {},
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    __typeEmits: {},
    __typeProps: {},
});
; /* PartiallyEnd: #4569/main.vue */
