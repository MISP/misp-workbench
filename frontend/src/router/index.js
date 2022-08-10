import { createRouter, createWebHistory } from "vue-router";

import { useAuthStore } from "@/stores";
import {
  HomeView,
  LoginView,
  IndexEventsView,
  ViewEventView,
  IndexUsersView,
  IndexOrganisationsView,
  ViewOrganisationView,
  ViewUsersView,
  IndexServersView,
  ViewServerView,
  EditEventView
} from "@/views";

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  linkActiveClass: "active",
  routes: [
    { path: "/", component: HomeView },
    { path: "/login", component: LoginView },
    { path: "/events", component: IndexEventsView },
    { path: "/events/:id", component: ViewEventView, props: true },
    { path: "/events/update/:id", component: EditEventView, props: true },
    { path: "/users", component: IndexUsersView },
    { path: "/users/:id", component: ViewUsersView, props: true },
    { path: "/organisations", component: IndexOrganisationsView },
    { path: "/organisations/:id", component: ViewOrganisationView, props: true },
    { path: "/servers", component: IndexServersView },
    { path: "/servers/:id", component: ViewServerView, props: true },
  ],
});

router.beforeEach(async (to) => {
  // redirect to login page if not logged in and trying to access a restricted page
  const publicPages = ["/login"];
  const authRequired = !publicPages.includes(to.path);
  const auth = useAuthStore();

  if (authRequired && !auth.isAuthenticated()) {
    auth.returnUrl = to.fullPath;
    return "/login";
  }
});
