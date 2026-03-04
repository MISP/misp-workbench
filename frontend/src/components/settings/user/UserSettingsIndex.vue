<script setup>
import { ref, reactive, onMounted, watch } from "vue";
import { storeToRefs } from "pinia";
import Spinner from "@/components/misc/Spinner.vue";
import { useUserSettingsStore, useToastsStore } from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faSync,
  faCode,
  faSlidersH,
  faTrash,
} from "@fortawesome/free-solid-svg-icons";

const toastsStore = useToastsStore();
const userSettingsStore = useUserSettingsStore();
const { userSettings, status } = storeToRefs(userSettingsStore);

const errors = ref({});
const editableSettings = reactive({});
const jsonMode = reactive({});

onMounted(() => {
  userSettingsStore.getAll().then(() => {
    Object.entries(userSettings.value).forEach(([namespace, value]) => {
      editableSettings[namespace] = JSON.stringify(value || {}, null, 4);
      jsonMode[namespace] = false;
    });
  });
});

watch(
  editableSettings,
  (newValues) => {
    for (const [namespace, jsonString] of Object.entries(newValues)) {
      try {
        JSON.parse(jsonString);
        errors.value[namespace] = null;
      } catch {
        errors.value[namespace] = "Invalid JSON";
      }
    }
  },
  { deep: true },
);

function toggleJsonMode(namespace) {
  if (!jsonMode[namespace]) {
    editableSettings[namespace] = JSON.stringify(
      userSettings.value[namespace] || {},
      null,
      4,
    );
  }
  jsonMode[namespace] = !jsonMode[namespace];
}

async function saveNamespace(namespace) {
  try {
    const parsed = JSON.parse(editableSettings[namespace]);
    await userSettingsStore.update(namespace, parsed);
    await userSettingsStore.getAll(true);
    errors.value[namespace] = null;
    toastsStore.push(
      `Settings for "${namespace}" updated successfully.`,
      "success",
    );
  } catch {
    errors.value[namespace] = "Invalid JSON";
  }
}

async function removeFollowedEntity(entityType, entityId) {
  const notifications = { ...(userSettings.value.notifications || {}) };
  const follow = { ...(notifications.follow || {}) };
  follow[entityType] = (follow[entityType] || []).filter(
    (id) => id !== entityId,
  );
  notifications.follow = follow;
  editableSettings.notifications = JSON.stringify(notifications, null, 4);
  await userSettingsStore.update("notifications", notifications);
  await userSettingsStore.getAll(true);
  toastsStore.push("Notifications settings updated.", "success");
}

async function removeSavedSearch(term) {
  const explore = { ...(userSettings.value.explore || {}) };
  explore.saved_searches = (explore.saved_searches || []).filter(
    (t) => t !== term,
  );
  editableSettings.explore = JSON.stringify(explore, null, 4);
  await userSettingsStore.update("explore", explore);
  await userSettingsStore.getAll(true);
  toastsStore.push("Explore settings updated.", "success");
}

const KNOWN_NAMESPACES = ["notifications", "explore"];
</script>

<template>
  <div class="container mt-4">
    <div class="row justify-content-center">
      <div class="col-md-12">
        <div class="card">
          <div class="card-header">
            <h3>User Settings</h3>
          </div>
          <div class="accordion m-4" id="settingsAccordion">
            <div
              class="accordion-item"
              v-for="(value, namespace) in userSettings"
              :key="namespace"
            >
              <h2 class="accordion-header" :id="`heading_${namespace}`">
                <button
                  class="accordion-button collapsed"
                  type="button"
                  data-bs-toggle="collapse"
                  :data-bs-target="`#collapse_${namespace}`"
                  aria-expanded="false"
                  :aria-controls="`collapse_${namespace}`"
                >
                  <strong>{{ namespace }}</strong>
                </button>
              </h2>

              <div
                :id="`collapse_${namespace}`"
                class="accordion-collapse collapse"
                :aria-labelledby="`heading_${namespace}`"
                data-bs-parent="#settingsAccordion"
              >
                <div class="accordion-body">
                  <!-- Mode toggle (only for known namespaces) -->
                  <div
                    v-if="KNOWN_NAMESPACES.includes(namespace)"
                    class="d-flex justify-content-end mb-3"
                  >
                    <div class="btn-group btn-group-sm" role="group">
                      <button
                        type="button"
                        class="btn"
                        :class="
                          !jsonMode[namespace]
                            ? 'btn-primary'
                            : 'btn-outline-secondary'
                        "
                        @click="jsonMode[namespace] = false"
                      >
                        <FontAwesomeIcon :icon="faSlidersH" class="me-1" />
                        Form
                      </button>
                      <button
                        type="button"
                        class="btn"
                        :class="
                          jsonMode[namespace]
                            ? 'btn-primary'
                            : 'btn-outline-secondary'
                        "
                        @click="toggleJsonMode(namespace)"
                      >
                        <FontAwesomeIcon :icon="faCode" class="me-1" />
                        JSON
                      </button>
                    </div>
                  </div>

                  <!-- ── notifications form ── -->
                  <template
                    v-if="namespace === 'notifications' && !jsonMode[namespace]"
                  >
                    <h6 class="text-muted mb-3">Followed Entities</h6>
                    <template
                      v-if="
                        value?.follow &&
                        Object.values(value.follow).some((ids) => ids?.length)
                      "
                    >
                      <div
                        v-for="(ids, entityType) in value.follow"
                        :key="entityType"
                        class="mb-3"
                      >
                        <label
                          v-if="ids?.length"
                          class="form-label fw-semibold text-capitalize"
                          >{{ entityType }}</label
                        >
                        <ul class="list-group" v-if="ids?.length">
                          <li
                            v-for="entityId in ids"
                            :key="entityId"
                            class="list-group-item d-flex justify-content-between align-items-center"
                          >
                            <RouterLink
                              :to="`/${entityType}/${entityId}`"
                              class="font-monospace small"
                              >{{ entityId }}</RouterLink
                            >
                            <button
                              type="button"
                              class="btn btn-outline-danger btn-sm"
                              title="Unfollow"
                              @click="
                                removeFollowedEntity(entityType, entityId)
                              "
                            >
                              <FontAwesomeIcon :icon="faTrash" />
                            </button>
                          </li>
                        </ul>
                      </div>
                    </template>
                    <p v-else class="text-muted">No followed entities.</p>
                  </template>

                  <!-- ── explore form ── -->
                  <template
                    v-else-if="namespace === 'explore' && !jsonMode[namespace]"
                  >
                    <h6 class="text-muted mb-3">Saved Searches</h6>
                    <ul class="list-group" v-if="value?.saved_searches?.length">
                      <li
                        v-for="term in value.saved_searches"
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
                    <p v-else class="text-muted">No saved searches.</p>
                  </template>

                  <!-- ── raw JSON (all namespaces in JSON mode, or unknown namespaces) ── -->
                  <template v-else>
                    <textarea
                      v-model="editableSettings[namespace]"
                      class="form-control font-monospace text-sm"
                      spellcheck="false"
                      :rows="
                        editableSettings[namespace]?.split('\n').length || 5
                      "
                      :class="{ 'is-invalid': errors[namespace] }"
                    />
                    <div class="invalid-feedback">{{ errors[namespace] }}</div>
                    <div class="d-flex justify-content-end mt-2">
                      <button
                        class="btn btn-primary btn-sm"
                        :disabled="!!errors[namespace]"
                        @click="saveNamespace(namespace)"
                      >
                        <FontAwesomeIcon
                          :icon="faSync"
                          spin
                          v-if="status.loading"
                        />
                        <span v-else>Save</span>
                      </button>
                    </div>
                  </template>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <Spinner v-if="status.loading" />
</template>
