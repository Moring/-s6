export const allRoutes = [
    // Default route - redirect to dashboard if authenticated, otherwise login
    {
        path: '/',
        redirect: (to: any) => {
            // This will be handled by the router guard
            return '/auth/login'
        },
    },

    // AfterResume Routes (protected)
    {
        path: '/afterresume',
        meta: { requiresAuth: true },
        redirect: '/afterresume/dashboard',
        children: [
            {
                path: 'dashboard',
                name: 'afterresume-dashboard',
                component: () => import('@/views/afterresume/dashboard/index.vue'),
                meta: { title: 'Dashboard', requiresAuth: true },
            },
            {
                path: 'worklog',
                name: 'afterresume-worklog',
                component: () => import('@/views/afterresume/worklog/index.vue'),
                meta: { title: 'Worklog', requiresAuth: true },
            },
            {
                path: 'worklog/clients',
                name: 'worklog-clients',
                component: () => import('@/views/afterresume/worklog/ClientsView.vue'),
                meta: { title: 'Clients & Employers', requiresAuth: true },
            },
            {
                path: 'worklog/projects',
                name: 'worklog-projects',
                component: () => import('@/views/afterresume/worklog/ProjectsView.vue'),
                meta: { title: 'Projects', requiresAuth: true },
            },
            {
                path: 'worklog/epics',
                name: 'worklog-epics',
                component: () => import('@/views/afterresume/worklog/EpicsView.vue'),
                meta: { title: 'Epics', requiresAuth: true },
            },
            {
                path: 'worklog/debug',
                name: 'worklog-debug',
                component: () => import('@/views/afterresume/worklog/debug.vue'),
                meta: { title: 'Worklog Debug', requiresAuth: true },
            },
            {
                path: 'skills',
                name: 'afterresume-skills',
                component: () => import('@/views/afterresume/skills/index.vue'),
                meta: { title: 'Skills Library', requiresAuth: true },
            },
            {
                path: 'reports',
                name: 'afterresume-reports',
                component: () => import('@/views/afterresume/reports/index.vue'),
                meta: { title: 'Reports', requiresAuth: true },
            },
            {
                path: 'artifacts',
                name: 'afterresume-artifacts',
                component: () => import('@/views/afterresume/artifacts/index.vue'),
                meta: { title: 'Artifacts', requiresAuth: true },
            },
            {
                path: 'billing',
                name: 'afterresume-billing',
                component: () => import('@/views/afterresume/billing/index.vue'),
                meta: { title: 'Billing', requiresAuth: true },
            },
            {
                path: 'admin',
                name: 'afterresume-admin',
                component: () => import('@/views/afterresume/admin/index.vue'),
                meta: { title: 'Admin', requiresAuth: true, requiresAdmin: true },
            },
        ],
    },

    // Auth Routes (public)
    {
        path: '/auth',
        children: [
            {
                path: 'login',
                name: 'auth-login',
                component: () => import('@/views/auth/afterresume/LoginView.vue'),
                meta: { title: 'Login', public: true },
            },
            {
                path: 'signup',
                name: 'auth-signup',
                component: () => import('@/views/auth/afterresume/SignupView.vue'),
                meta: { title: 'Sign Up', public: true },
            },
        ],
    },

    // 404 catch-all route - must be last
    {
        path: '/:pathMatch(.*)*',
        name: 'not-found',
        component: () => import('@/views/error/404/index.vue'),
        meta: { title: 'Not Found' },
    },
]
