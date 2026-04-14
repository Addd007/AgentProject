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
        }
        catch {
            store.setActiveSession(null);
        }
    }
});
function handleSelect(sessionId) {
    store.loadSessionDetail(sessionId);
}
function createConversation() {
    store.createSession();
}
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.section, __VLS_intrinsicElements.section)({
    ...{ class: "workspace-grid" },
});
/** @type {[typeof SessionSidebar, ]} */ ;
// @ts-ignore
const __VLS_0 = __VLS_asFunctionalComponent(SessionSidebar, new SessionSidebar({
    ...{ 'onCreate': {} },
    ...{ 'onSelect': {} },
    ...{ 'onDelete': {} },
    sessions: (__VLS_ctx.store.sessions),
    activeSessionId: (__VLS_ctx.store.activeSessionId),
    loading: (__VLS_ctx.store.isLoadingSessions),
}));
const __VLS_1 = __VLS_0({
    ...{ 'onCreate': {} },
    ...{ 'onSelect': {} },
    ...{ 'onDelete': {} },
    sessions: (__VLS_ctx.store.sessions),
    activeSessionId: (__VLS_ctx.store.activeSessionId),
    loading: (__VLS_ctx.store.isLoadingSessions),
}, ...__VLS_functionalComponentArgsRest(__VLS_0));
let __VLS_3;
let __VLS_4;
let __VLS_5;
const __VLS_6 = {
    onCreate: (__VLS_ctx.createConversation)
};
const __VLS_7 = {
    onSelect: (__VLS_ctx.handleSelect)
};
const __VLS_8 = {
    onDelete: (__VLS_ctx.store.deleteSession)
};
var __VLS_2;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "chat-stack" },
});
/** @type {[typeof ChatWindow, ]} */ ;
// @ts-ignore
const __VLS_9 = __VLS_asFunctionalComponent(ChatWindow, new ChatWindow({
    messages: (__VLS_ctx.store.activeMessages),
    loading: (__VLS_ctx.store.isSending),
}));
const __VLS_10 = __VLS_9({
    messages: (__VLS_ctx.store.activeMessages),
    loading: (__VLS_ctx.store.isSending),
}, ...__VLS_functionalComponentArgsRest(__VLS_9));
/** @type {[typeof MessageComposer, ]} */ ;
// @ts-ignore
const __VLS_12 = __VLS_asFunctionalComponent(MessageComposer, new MessageComposer({
    ...{ 'onSubmit': {} },
    ...{ 'onStop': {} },
    loading: (__VLS_ctx.store.isSending),
}));
const __VLS_13 = __VLS_12({
    ...{ 'onSubmit': {} },
    ...{ 'onStop': {} },
    loading: (__VLS_ctx.store.isSending),
}, ...__VLS_functionalComponentArgsRest(__VLS_12));
let __VLS_15;
let __VLS_16;
let __VLS_17;
const __VLS_18 = {
    onSubmit: (__VLS_ctx.store.sendMessage)
};
const __VLS_19 = {
    onStop: (__VLS_ctx.store.stopGenerating)
};
var __VLS_14;
/** @type {__VLS_StyleScopedClasses['workspace-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['chat-stack']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            ChatWindow: ChatWindow,
            MessageComposer: MessageComposer,
            SessionSidebar: SessionSidebar,
            store: store,
            handleSelect: handleSelect,
            createConversation: createConversation,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
