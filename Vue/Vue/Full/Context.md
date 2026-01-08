# Inspinia Vue 3 Admin Template – Context

This document captures how the Inspinia Vue 3 template is assembled so any AI coding agent can evolve the UI without guesswork. The key themes are **user-first design**, **reuse of the rich control set that already exists**, and **iterating until every screen is responsive, themed, and production-ready**.

## Purpose and Experience Principles
- Inspinia is a multi-application admin shell (CRM, eCommerce, analytics, etc.) that prizes clarity over novelty. Existing components are highly stylized—new features should compose them instead of recreating controls.
- Orientation, theme, and density are user-controlled. Every new view must respect `useLayout` state so features work in vertical, horizontal, condensed, offcanvas, or boxed modes without breaking.
- Consistency beats customization: typography, spacing, and iconography all flow from `src/assets/scss/app.scss` and Bootstrap variables. Never hard-code colors; rely on CSS variables or helper utilities such as `getColor`.
- Accessibility and responsiveness are non-negotiable. All layouts need to work down to 360px, keyboard focus should make sense, and chart/table colors must maintain contrast in both light and dark themes.

## Stack and Tooling
- Built with Vue 3 + TypeScript + Vite (`src/main.ts`) and BootstrapVue Next for layout primitives. Auto component registration via `unplugin-vue-components` means `<BContainer>`, `<BRow>`, etc. are globally available.
- Pinia (`src/stores/layout.ts`) handles the only global store today, and `pinia-plugin-persistedstate` keeps layout preferences in localStorage.
- Router configuration lives in `src/router/routes.ts`, imported into `src/router/index.ts` where a global guard applies HTML titles using `meta.title` and helper `appTitle`.
- Third-party UI libraries are pre-integrated: ApexCharts, ECharts, jsVectorMap, vue-multiselect, Choices.js, vue3-dropzone, SweetAlert2, vue3-tour, flatpickr, Quill, Ladda, FilePond, and more (see `package.json`). Their CSS baselines are imported once inside `src/main.ts`.
- Global typings for browser-only libraries are added in `src/globals.d.ts`.

## Application Shell
- `src/main.ts` bootstraps the app, registers Pinia, BootstrapVueNext, router, `vue3-tour`, `SimpleTypeahead`, and `@vueuse/head`, then mounts `App.vue`.
- `src/App.vue` renders the `Loader` overlay once and a `<RouterView />`. On mount it calls `useLayout().init()` so saved preferences immediately reapply by toggling attributes on `<html>`.
- `src/helpers/layout.ts` exposes `toggleAttribute`, `scrollToElement`, and easing helpers to keep DOM mutations centralized.

## Layout System and Navigation
- The `useLayout` store (`src/stores/layout.ts`) holds `skin`, `theme`, `orientation`, `topBar`/`sidenav` colors, `position`, `width`, and `isMobileMenuOpen`. Mutators update both store state and `<html>` attributes (`data-skin`, `data-bs-theme`, `data-layout`, etc.) so SCSS and Bootstrap variables react.
- Layouts are split into `MainLayout.vue`, `VerticalLayout.vue`, and `HorizontalLayout.vue`. `MainLayout` decides which child to render based on `layout.orientation`. Vertical layout renders `<Topbar>`, `<Sidenav>` or `<MobileMenu>`, the page slot, `<Footer>`, and `<Customizer>`. Horizontal layout swaps `<Navbar>` for `<Sidenav>` and enforces `data-layout="topnav"`.
- `Topbar` bundles logo links, the sidebar toggle button, a search bar, `MegaMenu`, language/messages/notifications dropdowns, theme toggler, customizer toggle, and user profile menu.
- `Sidenav` uses `simplebar` for a custom scrollbar, shows user info if enabled, and renders the hierarchical `menuItems` tree (defined in `src/layouts/components/data.ts`). `MenuItemWithChildren` recursively builds collapsible menus while keeping the active path expanded. `MobileMenu` wraps the same sidebar inside a `<BOffcanvas>` controlled by `layout.isMobileMenuOpen`.
- `Navbar` drives the horizontal experience using `horizontalMenuItems` from the same data module. Dropdown logic relies on the reusable `<Dropdown>` wrapper (Bootstrap JS).
- `Customizer` (`src/layouts/components/customizer/index.vue`) is an offcanvas panel that exposes every layout knob. When adding new layout options, extend the options arrays there and map them to store setters so toggles stay in sync.
- Any new navigation entry should be defined once in `menuItems`/`horizontalMenuItems` and once in `src/router/routes.ts`. The helper components will automatically pick them up.

## Shared Component Library
- **Page Scaffolding:** `PageBreadcrumb.vue` renders a two-level breadcrumb and title block. Most views also call `usePageMeta('Title')` to sync `<head>` tags.
- **Cards and Panels:** `UICard.vue` is the base for collapsible/reloadable/dismissable cards with consistent actions. Use it instead of raw `<BCard>` when you need toolbar controls.
- **Data Displays:** `TanstackTable.vue` wraps `@tanstack/vue-table` for sortable, empty-state-aware tables with optional action buttons. `TablePagination.vue` prints "Showing X to Y" copy and a consistent `<BPagination>` block.
- **Inputs:** `ChoicesInput.vue` / `ChoicesSelect.vue` wrap Choices.js to style selects and inputs. `MultiSelect.vue` wraps vue-multiselect. `TouchSpinInput.vue` adds spinner buttons around a number input. `FileUploader.vue` is a dropzone powered by `vue3-dropzone`. `PasswordStrengthBar.vue` and `Rating.vue` handle password meters and star ratings. Always import these first before building custom controls.
- **Charts and Visualizations:** `CustomApexChart.vue`, `CustomEChart.vue`, and `JsVectorMap.vue` encapsulate third-party chart packages. Instead of instantiating charts manually, pass a `getOptions` function so they can re-render when the layout theme or skin changes. Use `helpers/chart.ts` to fetch CSS variable colors/fonts dynamically.
- **Utility Blocks:** `TextDifferentView.vue` compares two strings using `diff` and applies brand colors. `Loader.vue` displays a spinner until the first frame is ready. `AuthLogo.vue`, `Dropdown.vue`, and others capture recurring patterns.
- All BootstrapVue components and directives are globally typed in `components.d.ts`, so you can use `<BRow>`, `<BDropdown>`, `v-b-tooltip`, etc. in any template.

## Views and Feature Modules
- Every screen lives under `src/views`, grouped by domain (`dashboards`, `apps`, `forms`, `tables`, `ui`, `graphs`, etc.). Within each feature you will typically see a `components/` folder for partials and a `data.ts` for mock data so markup stays readable.
- Composition pattern:
  1. Import and call `usePageMeta('Page Title')`.
  2. Wrap the body with `<MainLayout>` and `<BContainer fluid>`.
  3. Drop in `<PageBreadcrumb>` when there is a clear hierarchy.
  4. Use `<BRow>`/`<BCol>` to handle responsive grids; bootstrap utility classes are acceptable for spacing but prefer SCSS variables for colors.
  5. Pull charts/tables/form controls from the shared component set—e.g., eCommerce tables use `<TanstackTable>` plus `<TablePagination>`, and dashboards use `<CustomApexChart>` with options defined in their child components.
- Dynamic detail pages live in nested folders that mirror the URL (e.g., `views/apps/ecommerce/products/products/[id]/index.vue` matches `/products/:id`). Router params are accessible through `useRoute`.

## Routing Strategy
- `src/router/routes.ts` contains every registered path, grouped by feature with nested `children`. Lazy-loaded `() => import('...')` functions keep bundles small.
- Each route should define `meta.title` so the router guard in `src/router/index.ts` can set `document.title` to `${title} | ${appTitle}`. This feeds both SEO and the admin breadcrumb copy.
- When adding a route, ensure its URL matches the corresponding menu entry so the sidebar can highlight the correct item (`MenuItem` relies on `pathname.endsWith(item.url)`).

## Helpers and Composables
- `src/composables/usePageMeta.ts` centralizes `<head>` updates. `useClipboard`, `useViewport`, `useSystemTheme`, and `useTableActions` provide browser utilities without sprinkling DOM code everywhere.
- `src/helpers` cover string casing (`toPascalCase`, `toTitleCase`, `abbreviatedNumber`), chart colors (`getColor`, `getDefaultFontFamily`), fake data generation (`generateRandomEChartData`, `generateInitials`), byte formatting, and scroll/tween helpers. Favor these utilities instead of re-implementing logic in each view.

## Assets and Theming
- `src/assets/scss/app.scss` extends Bootstrap variables, registers component styles, and reads the `data-*` attributes that `useLayout` sets. Any new SCSS should hook into these attributes (`[data-skin="material"]`, `[data-menu-color="dark"]`, etc.) to stay compatible with the customizer.
- Logos, avatars, and layout thumbnail images live under `src/assets/images/`. Reference them through the alias import syntax (`@/assets/...`) so Vite handles bundling.

## Building New Experiences
1. **Plan state & data**: Identify whether the feature needs global settings (rare—extend `useLayout` sparingly) or local composables/store modules. Mock data in a colocated `data.ts` for quick iteration.
2. **Scaffold the view**: Duplicate the dashboard pattern—`MainLayout` + `BContainer/BRow/BCol` + `PageBreadcrumb` + `usePageMeta`. Start with skeleton cards using `UICard`.
3. **Wire controls**: Prefer the existing shared components. Examples:
   - Need tag filtering? Use `ChoicesSelect` plus `BFormSelect`.
   - Need drag-and-drop uploads? Use `FileUploader`.
   - Need adjustable numeric inputs? Use `TouchSpinInput`.
   - Need multi-select search? Use `MultiSelect`.
4. **Hook data**: If you need tables, use `TanstackTable` and `TablePagination` so sorting, empty states, and action buttons align with the rest of the app. For charts, supply a `getOptions` factory to the chart wrappers so they respond to theme changes.
5. **Register navigation**: Add the route to `routes.ts`, give it a `meta.title`, and update `menuItems`/`horizontalMenuItems` if it should appear in navigation.
6. **Polish and iterate**: Run through theme toggles, layout sizes (condensed, compact, on-hover, offcanvas), and orientation switches to ensure nothing overflows. Reuse the customizer to test each variant.

## Testing and Quality Loop
- Commands: `npm run dev` for interactive development, `npm run lint` for style issues, `npm run type-check` for TypeScript validation, and `npm run build` for release verification. Run lint/type-check before requesting review or shipping.
- Manual QA checklist per feature:
  - Verify the route title and breadcrumb copy are correct.
  - Check responsiveness at 1400px, 1200px, 992px, 768px, 576px, and 360px. Condensed and offcanvas sidebars should still expose the feature.
  - Toggle between light/dark/system themes and multiple skins to ensure SCSS selectors pick up the right colors.
  - Test the feature in both vertical and horizontal orientations.
  - Exercise relevant controls (dropdowns, modals, uploaders) with keyboard and pointer input.
  - If a screen surfaces data filters, confirm counts match `TablePagination` and that deletion/edit actions surface the right dialogs (SweetAlert2 is available for confirmations).
- Iterate until the GUI is functionally complete: start with wireframes, plug in data, confirm behavior, and refine visuals using the customizer to mimic user personalization.

Following this context ensures every new addition feels native to Inspinia, leverages the extensive control set, and honors the usability expectations Steve-Job level craftsmanship demands.
