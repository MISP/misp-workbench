<script setup>
import { ref, reactive, onMounted, watch } from "vue";
import { storeToRefs } from "pinia";
import Spinner from "@/components/misc/Spinner.vue";
import { useRuntimeSettingsStore } from "@/stores";

const runtimeSettingsStore = useRuntimeSettingsStore();
const { settings, status } = storeToRefs(runtimeSettingsStore);

const errors = ref({});
const editableSettings = reactive({});

onMounted(() => {
  runtimeSettingsStore.getAll().then(() => {
    Object.entries(settings.value).forEach(([namespace, value]) => {
      editableSettings[namespace] = JSON.stringify(value || {}, null, 4);
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

async function saveNamespace(namespace) {
  try {
    const parsed = JSON.parse(editableSettings[namespace]);
    await runtimeSettingsStore.update(namespace, parsed);
    await runtimeSettingsStore.getAll(); // Refresh
    errors.value[namespace] = null;
  } catch {
    errors.value[namespace] = "Invalid JSON";
  }
}
</script>

<template>
  <div class="container mt-4">
    <div class="row justify-content-center">
      <div class="col-md-12">
        <div class="card">
          <div class="card-header">
            <h3>Runtime Settings</h3>
          </div>
          <div class="accordion m-4" id="settingsAccordion">
            <div
              class="accordion-item"
              v-for="(value, namespace) in settings"
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
                  <textarea
                    v-model="editableSettings[namespace]"
                    class="form-control font-mono text-sm"
                    cols="40"
                    spellcheck="false"
                    :rows="editableSettings[namespace]?.split('\n').length || 5"
                    :class="{ 'is-invalid': errors[namespace] }"
                  />
                  <div class="invalid-feedback">{{ errors[namespace] }}</div>
                  <div class="d-flex justify-content-end mt-2">
                    <button
                      class="btn btn-primary text-sm"
                      @click="saveNamespace(namespace)"
                    >
                      Save
                    </button>
                  </div>
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
