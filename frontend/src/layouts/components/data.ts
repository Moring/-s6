import type { MenuItemType } from '@/types/layout'

type UserDropdownItemType = {
  label?: string
  icon?: string
  url?: string
  isDivider?: boolean
  isHeader?: boolean
  class?: string
}

export const userDropdownItems: UserDropdownItemType[] = [
  {
    label: 'Welcome back!',
    isHeader: true,
  },
  {
    label: 'Profile',
    icon: 'tabler:user-circle',
    url: '/afterresume/dashboard',
  },
  {
    label: 'Account Settings',
    icon: 'tabler:settings-2',
    url: '/afterresume/billing',
  },
  {
    isDivider: true,
  },
  {
    label: 'Log Out',
    icon: 'tabler:logout-2',
    url: '/auth/login',
    class: 'text-danger fw-semibold',
  },
]

export const menuItems: MenuItemType[] = [
    // Main Navigation
    { key: 'main', label: 'Main', isTitle: true },
    { 
        key: 'ar-dashboard', 
        label: 'Dashboard', 
        icon: 'tabler:layout-dashboard', 
        url: '/afterresume/dashboard' 
    },
    { 
        key: 'ar-worklog', 
        label: 'Worklog', 
        icon: 'tabler:notebook', 
        url: '/afterresume/worklog' 
    },
    { 
        key: 'ar-skills', 
        label: 'Skills', 
        icon: 'tabler:certificate', 
        url: '/afterresume/skills' 
    },
    { 
        key: 'ar-reports', 
        label: 'Reports', 
        icon: 'tabler:report', 
        url: '/afterresume/reports' 
    },
    { 
        key: 'ar-artifacts', 
        label: 'Artifacts', 
        icon: 'tabler:files', 
        url: '/afterresume/artifacts' 
    },
    { 
        key: 'ar-billing', 
        label: 'Billing', 
        icon: 'tabler:credit-card', 
        url: '/afterresume/billing' 
    },

    // Admin Section (shown only to admins)
    { key: 'admin', label: 'Admin', isTitle: true },
    { 
        key: 'ar-admin', 
        label: 'Admin Dashboard', 
        icon: 'tabler:shield-check', 
        url: '/afterresume/admin' 
    },
]

export const horizontalMenuItems: MenuItemType[] = [
    { 
        key: 'ar-dashboard', 
        label: 'Dashboard', 
        icon: 'tabler:layout-dashboard', 
        url: '/afterresume/dashboard' 
    },
    { 
        key: 'ar-worklog', 
        label: 'Worklog', 
        icon: 'tabler:notebook', 
        url: '/afterresume/worklog' 
    },
    { 
        key: 'ar-skills', 
        label: 'Skills', 
        icon: 'tabler:certificate', 
        url: '/afterresume/skills' 
    },
    { 
        key: 'ar-reports', 
        label: 'Reports', 
        icon: 'tabler:report', 
        url: '/afterresume/reports' 
    },
    { 
        key: 'ar-artifacts', 
        label: 'Artifacts', 
        icon: 'tabler:files', 
        url: '/afterresume/artifacts' 
    },
    { 
        key: 'ar-billing', 
        label: 'Billing', 
        icon: 'tabler:credit-card', 
        url: '/afterresume/billing' 
    },
    { 
        key: 'ar-admin', 
        label: 'Admin', 
        icon: 'tabler:shield-check', 
        url: '/afterresume/admin' 
    },
]
