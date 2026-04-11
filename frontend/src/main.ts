import { createApp } from 'vue';

import App from './App.vue';
import { pinia } from './pinia';
import router from './router';
import { useAuthStore } from './stores/auth';
import './styles/global.css';

const app = createApp(App);

app.use(pinia);
app.use(router);
app.mount('#app');

const authStore = useAuthStore(pinia);
const AUTH_CHECK_INTERVAL_MS = 60_000;

window.setInterval(async () => {
    const currentRoute = router.currentRoute.value;
    if (currentRoute.meta.public) {
        return;
    }

    const user = await authStore.validateSession();
    if (!user && !router.currentRoute.value.meta.public) {
        await router.replace('/auth');
    }
}, AUTH_CHECK_INTERVAL_MS);
