import { createRouter, createWebHistory } from 'vue-router';
import MainLayout from '../layouts/MainLayout.vue';
import { pinia } from '../pinia';
import { useAuthStore } from '../stores/auth';
import AuthPage from '../pages/AuthPage.vue';
import HomePage from '../pages/HomePage.vue';
import HistoryPage from '../pages/HistoryPage.vue';
const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: '/auth',
            name: 'auth',
            component: AuthPage,
            meta: { public: true },
        },
        {
            path: '/',
            component: MainLayout,
            children: [
                {
                    path: '',
                    name: 'home',
                    component: HomePage,
                },
                {
                    path: 'history',
                    name: 'history',
                    component: HistoryPage,
                },
            ],
        },
    ],
    scrollBehavior() {
        return { top: 0, behavior: 'smooth' };
    },
});
router.beforeEach(async (to) => {
    const authStore = useAuthStore(pinia);
    const user = await authStore.restoreSession();
    if (to.meta.public) {
        if (user && to.path === '/auth') {
            return '/';
        }
        return true;
    }
    if (!user) {
        return '/auth';
    }
    return true;
});
export default router;
