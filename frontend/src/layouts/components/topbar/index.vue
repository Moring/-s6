<template>
  <header class="app-topbar">
    <div class="container-fluid topbar-menu">
      <div class="d-flex align-items-center gap-2">
        <div class="logo-topbar">
          <RouterLink to="/afterresume/dashboard" class="logo-light">
            <span class="logo-lg">
              <span class="fw-bold fs-4">DigiMuse.AI</span>
            </span>
            <span class="logo-sm">
              <span class="fw-bold fs-4">DM</span>
            </span>
          </RouterLink>

          <RouterLink to="/afterresume/dashboard" class="logo-dark">
            <span class="logo-lg">
              <span class="fw-bold fs-4">DigiMuse.AI</span>
            </span>
            <span class="logo-sm">
              <span class="fw-bold fs-4">DM</span>
            </span>
          </RouterLink>
        </div>

        <!-- Sidebar Menu Toggle Button -->
        <button class="sidenav-toggle-button btn btn-primary btn-icon" @click="toggleSideNav">
          <Icon icon="tabler:menu-4" class="fs-22" />
        </button>

        <!-- Search -->
        <div class="app-search d-none d-xl-flex">
          <BFormInput
            type="search"
            class="topbar-search"
            name="search"
            placeholder="Search for something..."
          />
          <Icon icon="lucide:search"  class="app-search-icon text-muted" />
        </div>

      </div>

      <div class="d-flex align-items-center gap-2">
        <!-- <LanguageDropdown /> -->

        <!-- <MessageDropdown /> -->

        <NotificationDropdown />

        <!-- <CustomizerToggler /> -->

        <ThemeToggler />

        <UserProfile />
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import NotificationDropdown from '@/layouts/components/topbar/components/NotificationDropdown.vue'
import ThemeToggler from '@/layouts/components/topbar/components/ThemeToggler.vue'
import UserProfile from '@/layouts/components/topbar/components/UserProfile.vue'
import { useLayout } from '@/stores/layout.ts'
import { Icon } from '@iconify/vue'

const { layout, setSideNavSize, toggleMobileMenu } = useLayout()

const toggleSideNav = () => {
  const html = document.documentElement
  const currentSize = html.getAttribute('data-sidenav-size')

  if (currentSize === 'offcanvas') {
    toggleMobileMenu()
  } else if (layout.sidenav.size === 'compact') {
    setSideNavSize(currentSize === 'compact' ? 'condensed' : 'compact', false)
  } else {
    setSideNavSize(currentSize === 'condensed' ? 'default' : 'condensed')
  }
}
</script>
