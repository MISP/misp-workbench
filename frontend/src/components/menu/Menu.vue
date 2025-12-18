<script setup>
import { ref, watchEffect } from "vue";
import { useRouter } from "vue-router";
import { storeToRefs } from "pinia";
import { useAuthStore, useNotificationsStore } from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faBars,
  faBell,
  faMoon,
  faSun,
  faRightFromBracket,
} from "@fortawesome/free-solid-svg-icons";

const authStore = useAuthStore();
const router = useRouter();

// notifications
const notificationsStore = useNotificationsStore();
const { unreadNotifications } = storeToRefs(notificationsStore);
notificationsStore.getUnreadTotal();
setInterval(() => {
  notificationsStore.getUnreadTotal();
}, 10000);

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

const isMobileMenuOpen = ref(false);

function createBackdrop() {
  if (document.querySelector(".vue-offcanvas-backdrop")) return;
  const b = document.createElement("div");
  b.className = "vue-offcanvas-backdrop";
  Object.assign(b.style, {
    position: "fixed",
    inset: "0",
    background: "rgba(0,0,0,0.5)",
    zIndex: 1040,
  });
  b.addEventListener("click", closeMobileMenu);
  document.body.appendChild(b);
}

function removeBackdrop() {
  const b = document.querySelector(".vue-offcanvas-backdrop");
  if (b) {
    try {
      b.removeEventListener("click", closeMobileMenu);
    } finally {
      b.remove();
    }
  }
}

function openMobileMenu() {
  isMobileMenuOpen.value = true;
  document.body.classList.add("offcanvas-open");
  createBackdrop();
}

function closeMobileMenu() {
  isMobileMenuOpen.value = false;
  removeBackdrop();
  document.body.classList.remove("offcanvas-open");
  document.body.style.overflow = "";
  document.body.style.paddingRight = "";
}

function navAndClose(path) {
  closeMobileMenu();
  router.push(path).catch(() => {});
}
</script>

<style scoped>
.offcanvas-body ul,
.offcanvas-body ul ul {
  list-style: none;
  padding-left: 0;
  margin-left: 0;
}

.offcanvas-body ul ul {
  border-left: none !important;
  padding-left: 1rem;
}

.list-group-item {
  border: none !important;
}

.vue-offcanvas-backdrop {
  transition: opacity 0.15s linear;
}

.offcanvas.show {
  visibility: visible;
}
</style>

<template>
  <!-- ================= DESKTOP NAV ================= -->
  <nav v-if="!$isMobile" class="navbar navbar-expand border-bottom">
    <div class="container-fluid">
      <div class="navbar-nav">
        <RouterLink to="/" class="nav-item nav-link">
          <img src="/images/misp-logo-pixel.png" height="30" />
        </RouterLink>
        <RouterLink to="/explore" class="nav-item nav-link">explore</RouterLink>
        <RouterLink to="/events" class="nav-item nav-link">events</RouterLink>
        <RouterLink to="/users" class="nav-item nav-link">users</RouterLink>

        <div class="nav-item dropdown">
          <a
            class="nav-link dropdown-toggle"
            href="#"
            id="syncDropdown"
            role="button"
            data-bs-toggle="dropdown"
            aria-expanded="false"
          >
            sync
          </a>
          <ul class="dropdown-menu" aria-labelledby="syncDropdown">
            <li>
              <RouterLink to="/servers" class="dropdown-item"
                >servers</RouterLink
              >
            </li>
            <li><hr class="dropdown-divider" /></li>
            <li>
              <RouterLink to="/feeds" class="dropdown-item">feeds</RouterLink>
            </li>
          </ul>
        </div>

        <div class="nav-item dropdown">
          <a
            class="nav-link dropdown-toggle"
            href="#"
            id="internalsDropdown"
            role="button"
            data-bs-toggle="dropdown"
            aria-expanded="false"
          >
            internals
          </a>
          <ul class="dropdown-menu" aria-labelledby="internalsDropdown">
            <li>
              <RouterLink to="/organisations" class="dropdown-item"
                >organisations</RouterLink
              >
            </li>
            <li><hr class="dropdown-divider" /></li>
            <li>
              <RouterLink to="/settings/modules" class="dropdown-item"
                >modules</RouterLink
              >
            </li>
            <li><hr class="dropdown-divider" /></li>
            <li>
              <RouterLink to="/settings/taxonomies" class="dropdown-item"
                >taxonomies</RouterLink
              >
            </li>
            <li>
              <RouterLink to="/settings/galaxies" class="dropdown-item"
                >galaxies</RouterLink
              >
            </li>
            <li><hr class="dropdown-divider" /></li>
            <li>
              <RouterLink to="/correlations" class="dropdown-item"
                >correlations</RouterLink
              >
            </li>
            <li><hr class="dropdown-divider" /></li>
            <li>
              <RouterLink to="/tasks" class="dropdown-item">tasks</RouterLink>
            </li>
            <li><hr class="dropdown-divider" /></li>
            <li>
              <RouterLink to="/settings/runtime" class="dropdown-item"
                >runtime settings</RouterLink
              >
            </li>
            <li>
              <RouterLink to="/settings/user" class="dropdown-item"
                >user settings</RouterLink
              >
            </li>
          </ul>
        </div>
      </div>

      <div class="d-flex align-items-center gap-2">
        <button class="btn btn-outline" @click="switchTheme">
          <FontAwesomeIcon :icon="theme === 'light' ? faMoon : faSun" />
        </button>

        <RouterLink to="/notifications">
          <button class="btn btn-outline position-relative">
            <FontAwesomeIcon :icon="faBell" />
            <span
              v-if="unreadNotifications > 0"
              class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-info"
              style="font-size: 0.65rem"
            >
              {{ unreadNotifications }}
            </span>
          </button>
        </RouterLink>

        <button @click="authStore.logout()" class="btn btn-outline text-danger">
          <FontAwesomeIcon :icon="faRightFromBracket" />
        </button>
      </div>
    </div>
  </nav>

  <!-- ================= MOBILE NAV ================= -->
  <nav v-else class="navbar border-bottom sticky-top bg-body">
    <div class="container-fluid">
      <!-- Hamburger -->
      <button
        class="btn btn-outline"
        aria-label="Toggle menu"
        @click="openMobileMenu"
      >
        <FontAwesomeIcon :icon="faBars" />
      </button>

      <!-- Logo -->
      <RouterLink to="/" class="navbar-brand mx-auto">
        <img src="/images/misp-logo-pixel.png" height="28" />
      </RouterLink>

      <!-- Notifications -->
      <RouterLink to="/notifications">
        <button
          class="btn btn-outline position-relative"
          aria-label="Notifications"
        >
          <FontAwesomeIcon :icon="faBell" />
          <span
            v-if="unreadNotifications > 0"
            class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-info"
            style="font-size: 0.65rem"
          >
            {{ unreadNotifications }}
          </span>
        </button>
      </RouterLink>
    </div>
  </nav>

  <!-- ================= MOBILE OFFCANVAS ================= -->
  <div
    :class="['offcanvas offcanvas-start', { show: isMobileMenuOpen }]"
    tabindex="-1"
    id="mobileMenu"
    aria-labelledby="mobileMenuLabel"
  >
    <div class="offcanvas-header">
      <h5 class="offcanvas-title" id="mobileMenuLabel">Menu</h5>
      <button
        type="button"
        class="btn-close"
        aria-label="Close"
        @click="closeMobileMenu"
      />
    </div>

    <div class="offcanvas-body p-0">
      <ul class="list-group list-group-flush">
        <li>
          <RouterLink
            to="/explore"
            class="list-group-item list-group-item-action"
            @click.prevent="navAndClose('/explore')"
          >
            Explore
          </RouterLink>
        </li>
        <li>
          <RouterLink
            to="/events"
            class="list-group-item list-group-item-action"
            @click.prevent="navAndClose('/events')"
          >
            Events
          </RouterLink>
        </li>
        <li>
          <RouterLink
            to="/users"
            class="list-group-item list-group-item-action"
            @click.prevent="navAndClose('/users')"
          >
            Users
          </RouterLink>
        </li>

        <!-- Sync submenu -->
        <li class="list-group-item">
          <strong>Sync</strong>
          <ul class="list-group mt-2">
            <li>
              <RouterLink
                to="/servers"
                class="list-group-item list-group-item-action ps-4"
                @click.prevent="navAndClose('/servers')"
              >
                Servers
              </RouterLink>
            </li>
            <li>
              <RouterLink
                to="/feeds"
                class="list-group-item list-group-item-action ps-4"
                @click.prevent="navAndClose('/feeds')"
              >
                Feeds
              </RouterLink>
            </li>
          </ul>
        </li>

        <!-- Internals submenu -->
        <li class="list-group-item">
          <strong>Internals</strong>
          <ul class="list-group mt-2">
            <li>
              <RouterLink
                to="/organisations"
                class="list-group-item list-group-item-action ps-4"
                @click.prevent="navAndClose('/organisations')"
              >
                Organisations
              </RouterLink>
            </li>
            <li>
              <RouterLink
                to="/settings/modules"
                class="list-group-item list-group-item-action ps-4"
                @click.prevent="navAndClose('/settings/modules')"
              >
                Modules
              </RouterLink>
            </li>
            <li>
              <RouterLink
                to="/settings/taxonomies"
                class="list-group-item list-group-item-action ps-4"
                @click.prevent="navAndClose('/settings/taxonomies')"
              >
                Taxonomies
              </RouterLink>
            </li>
            <li>
              <RouterLink
                to="/settings/galaxies"
                class="list-group-item list-group-item-action ps-4"
                @click.prevent="navAndClose('/settings/galaxies')"
              >
                Galaxies
              </RouterLink>
            </li>
            <li>
              <RouterLink
                to="/correlations"
                class="list-group-item list-group-item-action ps-4"
                @click.prevent="navAndClose('/correlations')"
              >
                Correlations
              </RouterLink>
            </li>
            <li>
              <RouterLink
                to="/tasks"
                class="list-group-item list-group-item-action ps-4"
                @click.prevent="navAndClose('/tasks')"
              >
                Tasks
              </RouterLink>
            </li>
            <li>
              <RouterLink
                to="/settings/runtime"
                class="list-group-item list-group-item-action ps-4"
                @click.prevent="navAndClose('/settings/runtime')"
              >
                Runtime Settings
              </RouterLink>
            </li>
            <li>
              <RouterLink
                to="/settings/user"
                class="list-group-item list-group-item-action ps-4"
                @click.prevent="navAndClose('/settings/user')"
              >
                User Settings
              </RouterLink>
            </li>
          </ul>
        </li>
      </ul>

      <hr />

      <div class="d-flex justify-content-between align-items-center px-3">
        <button class="btn btn-outline" @click="switchTheme">
          <FontAwesomeIcon :icon="theme === 'light' ? faMoon : faSun" />
          <span class="ms-2">{{
            theme === "light" ? "Dark Mode" : "Light Mode"
          }}</span>
        </button>

        <button class="btn btn-outline text-danger" @click="authStore.logout()">
          <FontAwesomeIcon :icon="faRightFromBracket" />
          <span class="ms-2">Logout</span>
        </button>
      </div>
    </div>
  </div>
</template>
