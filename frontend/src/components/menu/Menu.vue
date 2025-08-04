<script setup>
import { ref, watchEffect } from "vue";
import { storeToRefs } from "pinia";
import { useAuthStore, useNotificationsStore } from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faArrowRightFromBracket,
  faBars,
  faBell,
  faBuilding,
  faEnvelopeOpenText,
  faMoon,
  faRightFromBracket,
  faServer,
  faSun,
} from "@fortawesome/free-solid-svg-icons";

const visible = ref(false);
const authStore = useAuthStore();

// fetch notifications and repeat every 10 seconds
const notificationsStore = useNotificationsStore();
const { unreadNotifications } = storeToRefs(notificationsStore);
notificationsStore.getUnreadTotal();
setInterval(() => {
  notificationsStore.getUnreadTotal();
}, 10000);

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
</script>

<style>
.mobile-menu-item {
  font-size: xx-large;
  line-height: 0;
  width: 5rem;
}
</style>

<template>
  <nav v-if="!$isMobile" class="navbar navbar-expand border-bottom">
    <div class="container-fluid">
      <div class="navbar-nav collapse navbar-collapse">
        <RouterLink to="/" class="nav-item nav-link">
          <img src="/images/misp-logo-pixel.png" alt="" height="30" />
        </RouterLink>
        <RouterLink to="/explore" class="nav-item nav-link">explore</RouterLink>
        <RouterLink to="/events" class="nav-item nav-link">events</RouterLink>
        <RouterLink to="/users" class="nav-item nav-link">users</RouterLink>
        <div class="nav-item dropdown">
          <a
            class="nav-link dropdown-toggle"
            href="#"
            id="navbarScrollingDropdown"
            role="button"
            data-bs-toggle="dropdown"
            aria-expanded="false"
          >
            sync
          </a>
          <ul class="dropdown-menu" aria-labelledby="navbarScrollingDropdown">
            <li>
              <RouterLink to="/servers" class="nav-item nav-link"
                >servers</RouterLink
              >
            </li>
            <hr class="dropdown-divider" />
            <li>
              <RouterLink to="/feeds" class="nav-item nav-link"
                >feeds</RouterLink
              >
            </li>
          </ul>
        </div>

        <div class="nav-item dropdown">
          <a
            class="nav-link dropdown-toggle"
            href="#"
            id="navbarScrollingDropdown"
            role="button"
            data-bs-toggle="dropdown"
            aria-expanded="false"
          >
            internals
          </a>
          <ul class="dropdown-menu" aria-labelledby="navbarScrollingDropdown">
            <li>
              <RouterLink to="/organisations" class="dropdown-item"
                >organisations</RouterLink
              >
            </li>
            <hr class="dropdown-divider" />
            <li>
              <RouterLink to="/settings/modules" class="dropdown-item"
                >modules</RouterLink
              >
            </li>
            <hr class="dropdown-divider" />
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
            <hr class="dropdown-divider" />
            <li>
              <RouterLink to="/correlations" class="dropdown-item"
                >correlations</RouterLink
              >
            </li>
            <hr class="dropdown-divider" />
            <li>
              <RouterLink to="/tasks" class="dropdown-item">tasks</RouterLink>
            </li>
            <hr class="dropdown-divider" />
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
      <div>
        <button type="button" class="btn btn-outline" @click="switchTheme">
          <FontAwesomeIcon
            v-if="theme == 'light'"
            :icon="faMoon"
            class="fa-xl"
          />
          <FontAwesomeIcon v-if="theme == 'dark'" :icon="faSun" class="fa-xl" />
        </button>
      </div>
      <div class="m-2">
        <RouterLink to="/notifications">
          <button type="button" class="btn btn-outline position-relative">
            <FontAwesomeIcon :icon="faBell" class="fa-xl" />

            <span
              v-if="unreadNotifications > 0"
              class="position-absolute start-80 translate-middle badge rounded-pill bg-danger"
              style="font-size: 0.65rem"
            >
              {{ unreadNotifications }}
              <span class="visually-hidden">unread notifications</span>
            </span>
          </button>
        </RouterLink>
      </div>
      <form class="d-flex">
        <button
          @click="authStore.logout()"
          class="btn btn-sm btn-outline text-danger"
          type="button"
        >
          <FontAwesomeIcon :icon="faRightFromBracket" class="fa-xl" />
        </button>
      </form>
    </div>
  </nav>
  <div v-if="$isMobile" class="sticky-top">
    <div>
      <a
        class="mobile-menu-item nav-pills nav-item nav-link d-block p-3 link-dark text-center border-end border-secondary"
        data-bs-toggle="collapse"
        href="#collapsable-menu"
        role="button"
        aria-expanded="false"
        aria-controls="collapsable-menu"
        @click="visible = !visible"
      >
        <FontAwesomeIcon :icon="faBars" inverse />
      </a>
    </div>
    <div class="position-absolute d-flex flex-column flex-shrink-0">
      <div id="collapsable-menu" :class="visible ? null : 'collapse'">
        <ul class="nav nav-pills nav-flush flex-column mb-auto text-center">
          <li class="nav-item mobile-menu-item">
            <RouterLink
              @click="visible = !visible"
              to="/events"
              class="nav-item nav-link py-3 border-bottom"
              aria-current="page"
              title=""
            >
              <FontAwesomeIcon :icon="faEnvelopeOpenText" inverse />
            </RouterLink>
          </li>
          <li class="nav-item mobile-menu-item">
            <RouterLink
              @click="visible = !visible"
              to="/organisations"
              class="nav-item nav-link mobile-menu-item nav-link py-3 border-bottom"
              title=""
            >
              <FontAwesomeIcon :icon="faBuilding" inverse />
            </RouterLink>
          </li>
          <li class="nav-item mobile-menu-item">
            <RouterLink
              @click="visible = !visible"
              to="/users"
              class="nav-item nav-link py-3 border-bottom"
              title=""
            >
              <FontAwesomeIcon :icon="faUsers" inverse />
            </RouterLink>
          </li>
          <li class="nav-item mobile-menu-item">
            <RouterLink
              @click="visible = !visible"
              to="/servers"
              class="nav-item nav-link py-3 border-bottom"
              title=""
            >
              <FontAwesomeIcon :icon="faServer" inverse />
            </RouterLink>
          </li>
          <li class="nav-item mobile-menu-item">
            <a
              @click="authStore.logout()"
              class="nav-item nav-link py-3 border-bottom"
              title=""
            >
              <FontAwesomeIcon :icon="faArrowRightFromBracket" inverse />
            </a>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>
