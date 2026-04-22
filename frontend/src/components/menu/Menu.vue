<script setup>
import { ref, watchEffect, computed } from "vue";
import { useRouter } from "vue-router";
import { storeToRefs } from "pinia";
import { useAuthStore, useNotificationsStore } from "@/stores";
import { authHelper } from "@/helpers";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faBars,
  faBell,
  faMoon,
  faSun,
  faRightFromBracket,
} from "@fortawesome/free-solid-svg-icons";
import AddEventButton from "@/components/events/AddEventButton.vue";

const authStore = useAuthStore();
const router = useRouter();
const { scopes } = storeToRefs(authStore);

const canReadUsers = computed(() =>
  authHelper.hasScope(scopes.value, "users:read"),
);
const canReadOrganisations = computed(() =>
  authHelper.hasScope(scopes.value, "organisations:read"),
);
const canReadTaxonomies = computed(() =>
  authHelper.hasScope(scopes.value, "taxonomies:read"),
);
const canReadGalaxies = computed(() =>
  authHelper.hasScope(scopes.value, "galaxies:read"),
);
const canReadCorrelations = computed(() =>
  authHelper.hasScope(scopes.value, "correlations:read"),
);
const canReadTasks = computed(() =>
  authHelper.hasScope(scopes.value, "tasks:read"),
);
const canReadDiagnostics = computed(() =>
  authHelper.hasScope(scopes.value, "diagnostics:read"),
);
const canReadSettings = computed(() =>
  authHelper.hasScope(scopes.value, "settings:read"),
);
const canReadUserSettings = computed(() =>
  authHelper.hasScope(scopes.value, "user_settings:read"),
);
const canReadApiKeys = computed(() =>
  authHelper.hasScope(scopes.value, "api_keys:read"),
);
const canAdminApiKeys = computed(() =>
  authHelper.hasScope(scopes.value, "api_keys:admin"),
);

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

.navbar-expand .navbar-nav .nav-link {
  line-height: 1.5em;
}
</style>

<template>
  <!-- ================= DESKTOP NAV ================= -->
  <nav v-if="!$isMobile" class="navbar navbar-expand border-bottom py-1">
    <div class="container-fluid">
      <div class="navbar-nav fw-light align-items-center">
        <RouterLink to="/" class="navbar-brand me-3 d-flex align-items-center">
          <img
            src="/images/misp-workbench-icon.png"
            height="26"
            alt="misp-workbench"
          />
        </RouterLink>
        <RouterLink to="/hunts" class="nav-item nav-link py-1">hunt</RouterLink>
        <RouterLink to="/explore" class="nav-item nav-link py-1"
          >explore</RouterLink
        >
        <div class="nav-item dropdown">
          <a
            class="nav-link dropdown-toggle py-1"
            href="#"
            id="syncDropdown"
            role="button"
            data-bs-toggle="dropdown"
            aria-expanded="false"
          >
            sources
          </a>
          <ul class="dropdown-menu" aria-labelledby="syncDropdown">
            <li>
              <RouterLink to="/feeds" class="dropdown-item fw-light"
                >feeds</RouterLink
              >
            </li>
            <li><hr class="dropdown-divider" /></li>
            <li>
              <RouterLink to="/servers" class="dropdown-item fw-light"
                >MISP servers</RouterLink
              >
            </li>
          </ul>
        </div>

        <div class="nav-item dropdown">
          <a
            class="nav-link dropdown-toggle py-1"
            href="#"
            id="internalsDropdown"
            role="button"
            data-bs-toggle="dropdown"
            aria-expanded="false"
          >
            internals
          </a>
          <ul class="dropdown-menu" aria-labelledby="internalsDropdown">
            <li v-if="canReadUsers">
              <RouterLink to="/users" class="dropdown-item fw-light"
                >users</RouterLink
              >
            </li>
            <li v-if="canReadOrganisations">
              <RouterLink to="/organisations" class="dropdown-item fw-light"
                >organisations</RouterLink
              >
            </li>
            <li>
              <RouterLink to="/roles" class="dropdown-item fw-light"
                >roles</RouterLink
              >
            </li>
            <li><hr class="dropdown-divider" /></li>
            <li>
              <RouterLink to="/settings/modules" class="dropdown-item fw-light"
                >modules</RouterLink
              >
            </li>
            <li><hr class="dropdown-divider" /></li>
            <li v-if="canReadTaxonomies">
              <RouterLink
                to="/settings/taxonomies"
                class="dropdown-item fw-light"
                >taxonomies</RouterLink
              >
            </li>
            <li v-if="canReadGalaxies">
              <RouterLink to="/settings/galaxies" class="dropdown-item fw-light"
                >galaxies</RouterLink
              >
            </li>
            <li><hr class="dropdown-divider" /></li>
            <li v-if="canReadCorrelations">
              <RouterLink to="/correlations" class="dropdown-item fw-light"
                >correlations</RouterLink
              >
            </li>
            <li><hr class="dropdown-divider" /></li>
            <li v-if="canReadTasks">
              <RouterLink to="/tasks" class="dropdown-item fw-light"
                >tasks</RouterLink
              >
            </li>
            <li v-if="canReadDiagnostics">
              <RouterLink to="/diagnostics" class="dropdown-item fw-light"
                >diagnostics</RouterLink
              >
            </li>
            <li><hr class="dropdown-divider" /></li>
            <li v-if="canReadSettings">
              <RouterLink to="/settings/runtime" class="dropdown-item fw-light"
                >runtime settings</RouterLink
              >
            </li>
            <li v-if="canReadUserSettings">
              <RouterLink to="/settings/user" class="dropdown-item fw-light"
                >user settings</RouterLink
              >
            </li>
            <li v-if="canReadApiKeys">
              <RouterLink to="/settings/api-keys" class="dropdown-item fw-light"
                >API keys</RouterLink
              >
            </li>
            <li v-if="canAdminApiKeys">
              <RouterLink to="/admin/api-keys" class="dropdown-item fw-light"
                >API keys (admin)</RouterLink
              >
            </li>
          </ul>
        </div>
      </div>

      <div class="d-flex align-items-center gap-2">
        <AddEventButton />
        <button class="btn btn-outline btn-sm" @click="switchTheme">
          <FontAwesomeIcon :icon="theme === 'light' ? faMoon : faSun" />
        </button>

        <RouterLink to="/notifications">
          <button class="btn btn-outline btn-sm position-relative">
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

        <button
          @click="authStore.logout()"
          class="btn btn-outline text-danger btn-sm"
        >
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
      <!-- <RouterLink to="/" class="navbar-brand mx-auto">
        <img
          src="/images/misp-lite-no-background.png"
          height="28"
          :style="{ filter: theme === 'dark' ? 'invert(1)' : 'none' }"
        />
      </RouterLink> -->

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
            to="/hunts"
            class="list-group-item list-group-item-action"
            @click.prevent="navAndClose('/hunts')"
          >
            hunt
          </RouterLink>
        </li>
        <li>
          <RouterLink
            to="/explore"
            class="list-group-item list-group-item-action"
            @click.prevent="navAndClose('/explore')"
          >
            explore
          </RouterLink>
        </li>
        <!-- Sources submenu -->
        <li class="list-group-item">
          <strong>sources</strong>
          <ul class="list-group mt-2">
            <li>
              <RouterLink
                to="/servers"
                class="list-group-item list-group-item-action ps-4"
                @click.prevent="navAndClose('/servers')"
              >
                servers
              </RouterLink>
            </li>
            <li>
              <RouterLink
                to="/feeds"
                class="list-group-item list-group-item-action ps-4"
                @click.prevent="navAndClose('/feeds')"
              >
                feeds
              </RouterLink>
            </li>
          </ul>
        </li>

        <!-- Internals submenu -->
        <li class="list-group-item">
          <strong>internals</strong>
          <ul class="list-group mt-2">
            <li v-if="canReadUsers">
              <RouterLink
                to="/users"
                class="list-group-item list-group-item-action ps-4"
                @click.prevent="navAndClose('/users')"
              >
                users
              </RouterLink>
            </li>
            <li v-if="canReadOrganisations">
              <RouterLink
                to="/organisations"
                class="list-group-item list-group-item-action ps-4"
                @click.prevent="navAndClose('/organisations')"
              >
                organisations
              </RouterLink>
            </li>
            <li>
              <RouterLink
                to="/roles"
                class="list-group-item list-group-item-action ps-4"
                @click.prevent="navAndClose('/roles')"
              >
                roles
              </RouterLink>
            </li>
            <li>
              <RouterLink
                to="/settings/modules"
                class="list-group-item list-group-item-action ps-4"
                @click.prevent="navAndClose('/settings/modules')"
              >
                modules
              </RouterLink>
            </li>
            <li v-if="canReadTaxonomies">
              <RouterLink
                to="/settings/taxonomies"
                class="list-group-item list-group-item-action ps-4"
                @click.prevent="navAndClose('/settings/taxonomies')"
              >
                taxonomies
              </RouterLink>
            </li>
            <li v-if="canReadGalaxies">
              <RouterLink
                to="/settings/galaxies"
                class="list-group-item list-group-item-action ps-4"
                @click.prevent="navAndClose('/settings/galaxies')"
              >
                galaxies
              </RouterLink>
            </li>
            <li v-if="canReadCorrelations">
              <RouterLink
                to="/correlations"
                class="list-group-item list-group-item-action ps-4"
                @click.prevent="navAndClose('/correlations')"
              >
                correlations
              </RouterLink>
            </li>
            <li v-if="canReadTasks">
              <RouterLink
                to="/tasks"
                class="list-group-item list-group-item-action ps-4"
                @click.prevent="navAndClose('/tasks')"
              >
                tasks
              </RouterLink>
            </li>
            <li v-if="canReadDiagnostics">
              <RouterLink
                to="/diagnostics"
                class="list-group-item list-group-item-action ps-4"
                @click.prevent="navAndClose('/diagnostics')"
              >
                diagnostics
              </RouterLink>
            </li>
            <li v-if="canReadSettings">
              <RouterLink
                to="/settings/runtime"
                class="list-group-item list-group-item-action ps-4"
                @click.prevent="navAndClose('/settings/runtime')"
              >
                runtime settings
              </RouterLink>
            </li>
            <li v-if="canReadUserSettings">
              <RouterLink
                to="/settings/user"
                class="list-group-item list-group-item-action ps-4"
                @click.prevent="navAndClose('/settings/user')"
              >
                user settings
              </RouterLink>
            </li>
            <li v-if="canReadApiKeys">
              <RouterLink
                to="/settings/api-keys"
                class="list-group-item list-group-item-action ps-4"
                @click.prevent="navAndClose('/settings/api-keys')"
              >
                API keys
              </RouterLink>
            </li>
            <li v-if="canAdminApiKeys">
              <RouterLink
                to="/admin/api-keys"
                class="list-group-item list-group-item-action ps-4"
                @click.prevent="navAndClose('/admin/api-keys')"
              >
                API keys (admin)
              </RouterLink>
            </li>
          </ul>
        </li>
      </ul>

      <hr />

      <div class="px-3 mb-3">
        <AddEventButton />
      </div>

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
