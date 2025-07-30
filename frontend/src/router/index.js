import { createRouter, createWebHistory } from "vue-router";

import { useAuthStore } from "@/stores";
import {
  Home,
  Login,
  IndexEvents,
  ViewEvent,
  IndexUsers,
  AddUser,
  ViewUser,
  EditUser,
  IndexOrganisations,
  ViewOrganisation,
  AddOrganisation,
  EditOrganisation,
  IndexServers,
  ViewServer,
  EditServer,
  AddServer,
  ExploreServer,
  EditEvent,
  AddEvent,
  ViewAttribute,
  EditAttribute,
  IndexModules,
  IndexFeeds,
  AddFeed,
  ViewFeed,
  UpdateFeed,
  IndexTaxonomies,
  ViewTaxonomy,
  IndexGalaxies,
  ViewGalaxy,
  ViewObject,
  EditObject,
  ViewRemoteEvent,
  ExploreEvents,
  TasksIndex,
  IndexCorrelations,
  IndexRuntimeSettings,
  IndexUserSettings,
  IndexNotifications,
} from "@/views";

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  linkActiveClass: "active",
  routes: [
    { path: "/", component: Home },
    { path: "/login", component: Login },
    { path: "/events", component: IndexEvents },
    { path: "/events/:uuid", component: ViewEvent, props: true },
    { path: "/events/update/:id", component: EditEvent, props: true },
    { path: "/events/add", component: AddEvent },
    { path: "/attributes/:id", component: ViewAttribute, props: true },
    { path: "/attributes/update/:id", component: EditAttribute, props: true },
    { path: "/objects/:id", component: ViewObject, props: true },
    { path: "/objects/update/:id", component: EditObject, props: true },
    { path: "/users", component: IndexUsers },
    { path: "/users/add", component: AddUser },
    { path: "/users/:id", component: ViewUser, props: true },
    { path: "/users/update/:id", component: EditUser, props: true },
    { path: "/organisations", component: IndexOrganisations },
    { path: "/organisations/:id", component: ViewOrganisation, props: true },
    { path: "/organisations/add", component: AddOrganisation },
    {
      path: "/organisations/update/:id",
      component: EditOrganisation,
      props: true,
    },
    { path: "/servers", component: IndexServers },
    { path: "/servers/:id", component: ViewServer, props: true },
    { path: "/servers/add", component: AddServer },
    { path: "/servers/update/:id", component: EditServer, props: true },
    { path: "/servers/explore/:id", component: ExploreServer, props: true },
    {
      path: "/servers/explore/:server_id/events/:event_uuid",
      component: ViewRemoteEvent,
      props: true,
    },
    { path: "/settings/modules", component: IndexModules },
    { path: "/settings/taxonomies", component: IndexTaxonomies },
    { path: "/settings/galaxies", component: IndexGalaxies },
    { path: "/feeds", component: IndexFeeds },
    { path: "/feeds/:id", component: ViewFeed, props: true },
    { path: "/feeds/add", component: AddFeed },
    { path: "/feeds/update/:id", component: UpdateFeed, props: true },
    { path: "/taxonomies/:id", component: ViewTaxonomy, props: true },
    { path: "/galaxies/:id", component: ViewGalaxy, props: true },
    { path: "/explore", component: ExploreEvents },
    { path: "/tasks", component: TasksIndex },
    { path: "/correlations", component: IndexCorrelations },
    { path: "/settings/runtime", component: IndexRuntimeSettings },
    { path: "/settings/user", component: IndexUserSettings },
    { path: "/notifications", component: IndexNotifications },
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
