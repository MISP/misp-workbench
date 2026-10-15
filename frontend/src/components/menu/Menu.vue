<script setup>
import { ref, watch, watchEffect, computed, nextTick, onUnmounted } from "vue";
import { useRoute } from "vue-router";
import { storeToRefs } from "pinia";
// Bootstrap's dropdowns (keyboard included) drive the menus. The same module
// as everywhere else: a second copy would register a second click handler,
// and every click would open the menu and close it again.
import { Dropdown } from "bootstrap";
import { useAuthStore, useNotificationsStore } from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faBars,
  faBell,
  faChevronDown,
  faMagnifyingGlass,
  faMoon,
  faRightFromBracket,
  faSun,
  faUser,
  faXmark,
} from "@fortawesome/free-solid-svg-icons";
import AddEventButton from "@/components/events/AddEventButton.vue";
import QuickSwitcher from "@/components/menu/QuickSwitcher.vue";
import { visibleMenu, visibleAccount, entryOf } from "@/components/menu/menu";

const authStore = useAuthStore();
const route = useRoute();
const { scopes, decoded_access_token } = storeToRefs(authStore);

const userEmail = computed(() => decoded_access_token.value?.sub || "");
const menu = computed(() => visibleMenu(scopes.value));
const account = computed(() => visibleAccount(scopes.value));

// Where the current page sits: its category is highlighted, its entry marked.
const current = computed(() => entryOf(route.path));
const activeCategory = computed(() => current.value?.category?.id ?? null);
const activeEntry = computed(() => current.value?.entry?.id ?? null);

// notifications
const notificationsStore = useNotificationsStore();
const { unreadNotifications } = storeToRefs(notificationsStore);
notificationsStore.getUnreadTotal();
const notificationsTimer = setInterval(() => {
  notificationsStore.getUnreadTotal();
}, 10000);
onUnmounted(() => clearInterval(notificationsTimer));
const notificationsLabel = computed(() =>
  unreadNotifications.value > 0
    ? `Notifications, ${unreadNotifications.value} unread`
    : "Notifications",
);

// theme
const theme = ref(localStorage.getItem("theme") || "light");

function setTheme(newTheme) {
  theme.value = newTheme;
  document.documentElement.setAttribute("data-bs-theme", newTheme);
  localStorage.setItem("theme", newTheme);
}

watchEffect(() => {
  setTheme(theme.value);
});

function switchTheme() {
  setTheme(theme.value === "light" ? "dark" : "light");
}

// quick switcher
const switcher = ref(null);
const isMac =
  typeof navigator !== "undefined" &&
  /Mac|iPhone|iPad/.test(navigator.platform);

// mobile menu
const isMobileMenuOpen = ref(false);
const openSection = ref(null);
const closeButton = ref(null);

async function openMobileMenu() {
  openSection.value = activeCategory.value;
  isMobileMenuOpen.value = true;
  document.body.classList.add("overflow-hidden");
  await nextTick();
  closeButton.value?.focus();
}

function closeMobileMenu() {
  isMobileMenuOpen.value = false;
  document.body.classList.remove("overflow-hidden");
}

function toggleSection(id) {
  openSection.value = openSection.value === id ? null : id;
}

// Following a link closes the menus, however it was followed (a key, the
// quick switcher).
const desktopNav = ref(null);
function closeDropdowns() {
  desktopNav.value
    ?.querySelectorAll('[data-bs-toggle="dropdown"]')
    .forEach((toggle) => Dropdown.getInstance(toggle)?.hide());
}
function openSwitcher() {
  closeDropdowns();
  switcher.value.open();
}
watch(
  () => route.fullPath,
  () => {
    closeDropdowns();
    closeMobileMenu();
  },
);
onUnmounted(closeMobileMenu);
</script>

<template>
  <!-- ================= DESKTOP ================= -->
  <nav
    ref="desktopNav"
    class="navbar navbar-expand border-bottom py-1 app-navbar d-none d-md-flex"
    aria-label="Main"
  >
    <div class="container-fluid gap-2">
      <RouterLink
        to="/"
        class="navbar-brand me-2 d-flex align-items-center"
        aria-label="misp-workbench home"
      >
        <img
          src="/images/misp-workbench-icon.png"
          height="26"
          alt="misp-workbench"
        />
      </RouterLink>

      <ul class="navbar-nav align-items-center gap-1 me-auto">
        <li
          v-for="category in menu"
          :key="category.id"
          class="nav-item dropdown"
        >
          <button
            :id="`nav-${category.id}`"
            type="button"
            class="nav-link app-nav-category dropdown-toggle"
            :class="{ active: activeCategory === category.id }"
            :aria-current="activeCategory === category.id ? 'true' : undefined"
            data-bs-toggle="dropdown"
            aria-expanded="false"
          >
            <FontAwesomeIcon :icon="category.icon" class="me-1 opacity-75" />
            {{ category.shortLabel || category.label }}
          </button>
          <div
            class="dropdown-menu app-mega-menu shadow-sm"
            :class="{ 'app-mega-menu-wide': category.entries.length > 4 }"
            :aria-labelledby="`nav-${category.id}`"
          >
            <div class="app-mega-menu-header">
              <span class="fw-semibold">{{ category.label }}</span>
              <span class="text-body-secondary">
                · {{ category.description }}</span
              >
            </div>
            <div class="app-mega-menu-grid">
              <RouterLink
                v-for="entry in category.entries"
                :key="entry.id"
                :to="entry.to"
                class="dropdown-item app-mega-item"
                :class="{ active: activeEntry === entry.id }"
                :aria-current="activeEntry === entry.id ? 'page' : undefined"
              >
                <span class="app-mega-icon" aria-hidden="true">
                  <FontAwesomeIcon :icon="entry.icon" fixed-width />
                </span>
                <span class="d-flex flex-column">
                  <span class="app-mega-label">{{ entry.label }}</span>
                  <span class="app-mega-description">{{
                    entry.description
                  }}</span>
                </span>
              </RouterLink>
            </div>
          </div>
        </li>
      </ul>

      <button
        type="button"
        class="btn btn-sm app-search-button d-flex align-items-center gap-2"
        aria-label="Search pages, events and indicators"
        @click="openSwitcher"
      >
        <FontAwesomeIcon :icon="faMagnifyingGlass" class="opacity-75" />
        <span class="d-none d-lg-inline">Search or jump to…</span>
        <kbd class="d-none d-lg-inline">{{ isMac ? "⌘" : "Ctrl" }} K</kbd>
      </button>

      <div class="d-flex align-items-center gap-2">
        <AddEventButton />
        <button
          type="button"
          class="btn btn-outline btn-sm"
          :aria-label="
            theme === 'light' ? 'Switch to dark theme' : 'Switch to light theme'
          "
          :title="
            theme === 'light' ? 'Switch to dark theme' : 'Switch to light theme'
          "
          @click="switchTheme"
        >
          <FontAwesomeIcon :icon="theme === 'light' ? faMoon : faSun" />
        </button>

        <RouterLink
          to="/notifications"
          class="btn btn-outline btn-sm position-relative"
          :class="{ active: route.path.startsWith('/notifications') }"
          :aria-label="notificationsLabel"
          :title="notificationsLabel"
        >
          <FontAwesomeIcon :icon="faBell" />
          <span
            v-if="unreadNotifications > 0"
            class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-info"
            style="font-size: 0.65rem"
            aria-hidden="true"
          >
            {{ unreadNotifications }}
          </span>
        </RouterLink>

        <div class="dropdown">
          <button
            id="nav-account"
            type="button"
            class="btn btn-outline btn-sm dropdown-toggle"
            :class="{ active: current && !current.category }"
            data-bs-toggle="dropdown"
            aria-expanded="false"
            aria-label="Account"
          >
            <FontAwesomeIcon :icon="faUser" />
          </button>
          <ul
            class="dropdown-menu dropdown-menu-end shadow-sm"
            aria-labelledby="nav-account"
          >
            <li v-if="userEmail">
              <span class="dropdown-item-text small text-body-secondary">{{
                userEmail
              }}</span>
            </li>
            <li v-if="userEmail"><hr class="dropdown-divider" /></li>
            <li v-for="entry in account" :key="entry.id">
              <RouterLink
                :to="entry.to"
                class="dropdown-item"
                :class="{ active: activeEntry === entry.id }"
              >
                <FontAwesomeIcon :icon="entry.icon" fixed-width class="me-2" />
                {{ entry.label }}
              </RouterLink>
            </li>
            <li><hr class="dropdown-divider" /></li>
            <li>
              <button
                type="button"
                class="dropdown-item text-danger"
                @click="authStore.logout()"
              >
                <FontAwesomeIcon
                  :icon="faRightFromBracket"
                  fixed-width
                  class="me-2"
                />
                Sign out
              </button>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </nav>

  <!-- ================= MOBILE ================= -->
  <nav
    class="navbar border-bottom sticky-top bg-body app-navbar d-flex d-md-none"
    aria-label="Main"
  >
    <div class="container-fluid gap-2">
      <button
        type="button"
        class="btn btn-outline app-touch"
        aria-label="Open menu"
        aria-controls="mobileMenu"
        :aria-expanded="isMobileMenuOpen ? 'true' : 'false'"
        @click="openMobileMenu"
      >
        <FontAwesomeIcon :icon="faBars" />
      </button>
      <span class="me-auto small fw-semibold text-truncate">
        {{ current?.entry?.label || "" }}
      </span>
      <button
        type="button"
        class="btn btn-outline app-touch"
        aria-label="Search pages, events and indicators"
        @click="openSwitcher"
      >
        <FontAwesomeIcon :icon="faMagnifyingGlass" />
      </button>
      <RouterLink
        to="/notifications"
        class="btn btn-outline app-touch position-relative"
        :aria-label="notificationsLabel"
      >
        <FontAwesomeIcon :icon="faBell" />
        <span
          v-if="unreadNotifications > 0"
          class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-info"
          style="font-size: 0.65rem"
          aria-hidden="true"
        >
          {{ unreadNotifications }}
        </span>
      </RouterLink>
    </div>
  </nav>

  <div
    v-if="isMobileMenuOpen"
    class="offcanvas-backdrop fade show d-md-none"
    @click="closeMobileMenu"
  ></div>
  <div
    id="mobileMenu"
    class="offcanvas offcanvas-start d-md-none"
    :class="{ show: isMobileMenuOpen }"
    tabindex="-1"
    role="dialog"
    aria-modal="true"
    aria-labelledby="mobileMenuLabel"
    :aria-hidden="isMobileMenuOpen ? undefined : 'true'"
    :inert="!isMobileMenuOpen || undefined"
    @keydown.esc="closeMobileMenu"
  >
    <div class="offcanvas-header border-bottom">
      <h5
        id="mobileMenuLabel"
        class="offcanvas-title d-flex align-items-center gap-2"
      >
        <img src="/images/misp-workbench-icon.png" height="22" alt="" />
        Menu
      </h5>
      <button
        ref="closeButton"
        type="button"
        class="btn btn-outline app-touch ms-auto"
        aria-label="Close menu"
        @click="closeMobileMenu"
      >
        <FontAwesomeIcon :icon="faXmark" />
      </button>
    </div>

    <div class="offcanvas-body p-0">
      <div class="p-3 border-bottom d-flex gap-2">
        <AddEventButton />
      </div>
      <ul class="list-unstyled mb-0">
        <li v-for="category in menu" :key="category.id" class="border-bottom">
          <button
            :id="`mobile-nav-${category.id}`"
            type="button"
            class="btn w-100 text-start d-flex align-items-center gap-2 app-touch app-mobile-section"
            :class="{ 'text-primary': activeCategory === category.id }"
            :aria-expanded="openSection === category.id ? 'true' : 'false'"
            :aria-controls="`mobile-nav-${category.id}-entries`"
            @click="toggleSection(category.id)"
          >
            <FontAwesomeIcon :icon="category.icon" fixed-width />
            <span class="fw-semibold">{{ category.label }}</span>
            <FontAwesomeIcon
              :icon="faChevronDown"
              class="ms-auto small app-chevron"
              :class="{ 'app-chevron-open': openSection === category.id }"
            />
          </button>
          <ul
            v-show="openSection === category.id"
            :id="`mobile-nav-${category.id}-entries`"
            class="list-unstyled mb-2"
            :aria-labelledby="`mobile-nav-${category.id}`"
          >
            <li v-for="entry in category.entries" :key="entry.id">
              <RouterLink
                :to="entry.to"
                class="d-flex align-items-start gap-2 px-4 py-2 text-decoration-none app-mobile-entry"
                :class="{ active: activeEntry === entry.id }"
                :aria-current="activeEntry === entry.id ? 'page' : undefined"
              >
                <FontAwesomeIcon
                  :icon="entry.icon"
                  fixed-width
                  class="mt-1 opacity-75"
                />
                <span class="d-flex flex-column">
                  <span>{{ entry.label }}</span>
                  <span class="small text-body-secondary">{{
                    entry.description
                  }}</span>
                </span>
              </RouterLink>
            </li>
          </ul>
        </li>
      </ul>

      <div class="p-3">
        <div v-if="userEmail" class="small text-body-secondary mb-2">
          {{ userEmail }}
        </div>
        <ul class="list-unstyled mb-2">
          <li v-for="entry in account" :key="entry.id">
            <RouterLink
              :to="entry.to"
              class="d-flex align-items-center gap-2 py-2 text-decoration-none app-mobile-entry app-touch"
              :class="{ active: activeEntry === entry.id }"
            >
              <FontAwesomeIcon :icon="entry.icon" fixed-width />
              {{ entry.label }}
            </RouterLink>
          </li>
        </ul>
        <div class="d-flex gap-2">
          <button
            type="button"
            class="btn btn-outline-secondary app-touch flex-fill"
            @click="switchTheme"
          >
            <FontAwesomeIcon
              :icon="theme === 'light' ? faMoon : faSun"
              class="me-1"
            />
            {{ theme === "light" ? "Dark theme" : "Light theme" }}
          </button>
          <button
            type="button"
            class="btn btn-outline-danger app-touch flex-fill"
            @click="authStore.logout()"
          >
            <FontAwesomeIcon :icon="faRightFromBracket" class="me-1" />
            Sign out
          </button>
        </div>
      </div>
    </div>
  </div>

  <QuickSwitcher ref="switcher" @opening="closeDropdowns" />
</template>

<style scoped>
.app-nav-category {
  border: 0;
  background: none;
  border-radius: 0.375rem;
  padding: 0.3rem 0.6rem !important;
  font-size: 0.95rem;
}
.app-nav-category:hover,
.app-nav-category[aria-expanded="true"] {
  background: var(--bs-tertiary-bg);
}
.app-nav-category.active {
  color: var(--bs-primary) !important;
  background: var(--bs-primary-bg-subtle);
}
.app-nav-category:focus-visible,
.app-search-button:focus-visible,
.app-mega-item:focus-visible,
.app-mobile-section:focus-visible,
.app-mobile-entry:focus-visible {
  outline: 2px solid var(--bs-primary);
  outline-offset: 2px;
}

.app-mega-menu {
  width: 22rem;
  padding: 0.5rem;
}
.app-mega-menu-wide {
  width: 40rem;
}
.app-mega-menu-header {
  font-size: 0.8rem;
  padding: 0.25rem 0.5rem 0.5rem;
  border-bottom: 1px solid var(--bs-border-color-translucent);
  margin-bottom: 0.25rem;
}
.app-mega-menu-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.125rem;
}
.app-mega-menu-wide .app-mega-menu-grid {
  grid-template-columns: 1fr 1fr;
}
.app-mega-item {
  display: flex;
  gap: 0.6rem;
  align-items: flex-start;
  white-space: normal;
  border-radius: 0.375rem;
  padding: 0.45rem 0.5rem;
}
.app-mega-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  width: 2rem;
  height: 2rem;
  border-radius: 0.375rem;
  background: var(--bs-tertiary-bg);
  color: var(--bs-primary);
}
.app-mega-label {
  font-weight: 500;
  line-height: 1.3;
}
.app-mega-description {
  font-size: 0.78rem;
  color: var(--bs-secondary-color);
  line-height: 1.3;
}
.app-mega-item.active,
.app-mega-item:active {
  background: var(--bs-primary-bg-subtle);
  color: var(--bs-emphasis-color);
}
.app-mega-item.active .app-mega-description,
.app-mega-item:active .app-mega-description {
  color: var(--bs-secondary-color);
}

.app-search-button {
  border: 1px solid var(--bs-border-color);
  color: var(--bs-secondary-color);
  background: var(--bs-body-bg);
}
.app-search-button:hover {
  background: var(--bs-tertiary-bg);
}
.app-search-button kbd {
  font-size: 0.7rem;
  background: var(--bs-tertiary-bg);
  color: var(--bs-secondary-color);
  border: 1px solid var(--bs-border-color);
}

/* Touch targets at least 44px. */
.app-touch {
  min-height: 44px;
  min-width: 44px;
}
.app-mobile-section {
  padding: 0.5rem 1rem;
  border-radius: 0;
}
.app-chevron {
  transition: transform 0.15s ease;
}
.app-chevron-open {
  transform: rotate(180deg);
}
.app-mobile-entry {
  color: var(--bs-body-color);
  min-height: 44px;
}
.app-mobile-entry.active {
  color: var(--bs-primary);
  background: var(--bs-primary-bg-subtle);
}
.offcanvas {
  visibility: hidden;
}
.offcanvas.show {
  visibility: visible;
}
</style>
