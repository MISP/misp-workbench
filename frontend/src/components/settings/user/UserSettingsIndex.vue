<script setup>
import { ref, reactive, computed, onMounted, watch } from "vue";
import { storeToRefs } from "pinia";
import Spinner from "@/components/misc/Spinner.vue";
import { useUserSettingsStore, useToastsStore } from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faTrash, faBell, faCompass } from "@fortawesome/free-solid-svg-icons";

const toastsStore = useToastsStore();
const userSettingsStore = useUserSettingsStore();
const { userSettings, status } = storeToRefs(userSettingsStore);

// Default values mirrored from api/app/defaults/runtime_settings_defaults.py.
// Shown as helper text only — users with the "settings:read" scope are not
// guaranteed, so we don't fetch the runtime overlay here.
const NOTIFICATIONS_DEFAULTS = {
  email_max_per_hour: 10,
};

const notificationsForm = reactive({
  email_max_per_hour: "",
});

const errors = reactive({
  email_max_per_hour: null,
});

const notifications = computed(() => userSettings.value?.notifications || {});
const explore = computed(() => userSettings.value?.explore || {});

const followedEntities = computed(() => notifications.value.follow || {});
const hasFollowedEntities = computed(() =>
  Object.values(followedEntities.value).some((ids) => ids?.length),
);

const savedSearches = computed(() => explore.value.saved_searches || []);

function syncForm() {
  const v = notifications.value.email_max_per_hour;
  notificationsForm.email_max_per_hour = typeof v === "number" ? v : "";
}

onMounted(async () => {
  await userSettingsStore.getAll();
  syncForm();
});

watch(notifications, syncForm, { deep: true });

async function saveEmailMaxPerHour() {
  const raw = notificationsForm.email_max_per_hour;
  let value;
  if (raw === "" || raw === null || raw === undefined) {
    value = null;
  } else {
    value = Number(raw);
    if (!Number.isFinite(value) || value < 0 || !Number.isInteger(value)) {
      errors.email_max_per_hour = "Must be a non-negative integer.";
      return;
    }
  }
  errors.email_max_per_hour = null;

  const next = { ...notifications.value };
  if (value === null) {
    delete next.email_max_per_hour;
  } else {
    next.email_max_per_hour = value;
  }
  await userSettingsStore.update("notifications", next);
  toastsStore.push("Notification settings updated.", "success");
}

async function removeFollowedEntity(entityType, entityId) {
  const next = { ...notifications.value };
  const follow = { ...(next.follow || {}) };
  follow[entityType] = (follow[entityType] || []).filter(
    (id) => id !== entityId,
  );
  next.follow = follow;
  await userSettingsStore.update("notifications", next);
  toastsStore.push("Notification settings updated.", "success");
}

async function removeSavedSearch(term) {
  const next = { ...explore.value };
  next.saved_searches = (next.saved_searches || []).filter((t) => t !== term);
  await userSettingsStore.update("explore", next);
  toastsStore.push("Explore settings updated.", "success");
}

// Anything stored under a namespace we don't render a form for. We don't
// expose a JSON editor here — surface them so the user knows they exist
// and can remove them.
const KNOWN_NAMESPACES = ["notifications", "explore"];
const otherNamespaces = computed(() =>
  Object.keys(userSettings.value || {}).filter(
    (ns) => !KNOWN_NAMESPACES.includes(ns),
  ),
);

async function deleteNamespace(namespace) {
  if (
    !confirm(
      `Delete the "${namespace}" settings? This restores system defaults.`,
    )
  ) {
    return;
  }
  await userSettingsStore.delete(namespace);
  await userSettingsStore.getAll(true);
  toastsStore.push(`Removed "${namespace}" settings.`, "success");
}

const initialLoad = ref(true);
watch(
  () => status.value.loading,
  (loading) => {
    if (!loading && userSettings.value !== null) initialLoad.value = false;
  },
);
</script>

<template>
  <div class="container mt-4">
    <div class="row justify-content-center">
      <div class="col-md-10">
        <div class="card mb-4">
          <div class="card-header">
            <h3 class="mb-0">User Settings</h3>
          </div>

          <Spinner v-if="initialLoad && status.loading" />

          <template v-else>
            <!-- ──────── Notifications ──────── -->
            <div class="card-body border-bottom">
              <h5 class="mb-3">
                <FontAwesomeIcon :icon="faBell" class="me-2" />
                Notifications
              </h5>

              <h6 class="text-muted mb-3">Email</h6>
              <div class="mb-4">
                <label for="emailMaxPerHour" class="form-label">
                  Max emails per hour
                </label>
                <div class="d-flex align-items-start gap-2">
                  <input
                    id="emailMaxPerHour"
                    type="number"
                    min="0"
                    step="1"
                    class="form-control"
                    style="max-width: 10rem"
                    :class="{ 'is-invalid': errors.email_max_per_hour }"
                    v-model="notificationsForm.email_max_per_hour"
                    :placeholder="`${NOTIFICATIONS_DEFAULTS.email_max_per_hour} (default)`"
                  />
                  <button
                    type="button"
                    class="btn btn-primary"
                    :disabled="status.updating"
                    @click="saveEmailMaxPerHour"
                  >
                    Save
                  </button>
                </div>
                <div
                  v-if="errors.email_max_per_hour"
                  class="text-danger small mt-1"
                >
                  {{ errors.email_max_per_hour }}
                </div>
                <small class="form-text text-muted d-block mt-1">
                  Maximum notification emails sent to you per hour. Set to
                  <code>0</code> to disable the limit. Leave empty to inherit
                  the system default (<code>{{
                    NOTIFICATIONS_DEFAULTS.email_max_per_hour
                  }}</code
                  >).
                </small>
              </div>

              <h6 class="text-muted mb-3">Followed entities</h6>
              <template v-if="hasFollowedEntities">
                <div
                  v-for="(ids, entityType) in followedEntities"
                  :key="entityType"
                  class="mb-3"
                >
                  <template v-if="ids?.length">
                    <label class="form-label fw-semibold text-capitalize">
                      {{ entityType }}
                    </label>
                    <ul class="list-group">
                      <li
                        v-for="entityId in ids"
                        :key="entityId"
                        class="list-group-item d-flex justify-content-between align-items-center"
                      >
                        <RouterLink
                          :to="`/${entityType}/${entityId}`"
                          class="font-monospace small"
                        >
                          {{ entityId }}
                        </RouterLink>
                        <button
                          type="button"
                          class="btn btn-outline-danger btn-sm"
                          title="Unfollow"
                          @click="removeFollowedEntity(entityType, entityId)"
                        >
                          <FontAwesomeIcon :icon="faTrash" />
                        </button>
                      </li>
                    </ul>
                  </template>
                </div>
              </template>
              <p v-else class="text-muted mb-0">
                You aren't following any entities. Open an event, attribute, or
                organisation and click the follow button to start receiving
                notifications about it.
              </p>
            </div>

            <!-- ──────── Explore ──────── -->
            <div class="card-body">
              <h5 class="mb-3">
                <FontAwesomeIcon :icon="faCompass" class="me-2" />
                Explore
              </h5>

              <h6 class="text-muted mb-3">Saved searches</h6>
              <ul v-if="savedSearches.length" class="list-group">
                <li
                  v-for="term in savedSearches"
                  :key="term"
                  class="list-group-item d-flex justify-content-between align-items-center"
                >
                  <code class="small">{{ term }}</code>
                  <button
                    type="button"
                    class="btn btn-outline-danger btn-sm"
                    title="Remove"
                    @click="removeSavedSearch(term)"
                  >
                    <FontAwesomeIcon :icon="faTrash" />
                  </button>
                </li>
              </ul>
              <p v-else class="text-muted mb-0">
                No saved searches. Run a query in
                <RouterLink to="/explore">explore</RouterLink> and save it from
                the search bar to keep it handy.
              </p>
            </div>

            <!-- ──────── Other namespaces (cleanup-only) ──────── -->
            <div v-if="otherNamespaces.length" class="card-body border-top">
              <h6 class="text-muted mb-3">Other stored settings</h6>
              <p class="small text-muted">
                These namespaces are stored on your account but don't have an
                editor on this page. You can remove them to fall back to system
                defaults.
              </p>
              <ul class="list-group">
                <li
                  v-for="ns in otherNamespaces"
                  :key="ns"
                  class="list-group-item d-flex justify-content-between align-items-center"
                >
                  <code>{{ ns }}</code>
                  <button
                    type="button"
                    class="btn btn-outline-danger btn-sm"
                    @click="deleteNamespace(ns)"
                  >
                    <FontAwesomeIcon :icon="faTrash" class="me-1" />
                    Remove
                  </button>
                </li>
              </ul>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
