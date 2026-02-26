<script setup>
import { ref, reactive, computed } from "vue";
import { useHuntsStore, useToastsStore } from "@/stores";
import LuceneQuerySyntaxHint from "@/components/misc/LuceneQuerySyntaxHint.vue";
import EventsPropertiesModal from "@/components/misc/EventsPropertiesModal.vue";
import AttributesPropertiesModal from "@/components/misc/AttributesPropertiesModal.vue";
import CorrelationPropertiesModal from "@/components/misc/CorrelationPropertiesModal.vue";

const props = defineProps({
  initialQuery: { type: String, default: "" },
  initialIndexTarget: { type: String, default: "attributes" },
});

const huntsStore = useHuntsStore();
const toastsStore = useToastsStore();

const emit = defineEmits(["created", "close"]);

const hunt = reactive({
  name: "",
  description: "",
  query: props.initialQuery,
  index_target: props.initialIndexTarget,
  status: "active",
});

const apiError = ref(null);

const canSubmit = computed(() => hunt.name && hunt.query);

function reset() {
  hunt.name = "";
  hunt.description = "";
  hunt.query = props.initialQuery;
  hunt.index_target = props.initialIndexTarget;
  hunt.status = "active";
  apiError.value = null;
}

async function submit() {
  apiError.value = null;
  await huntsStore
    .create({ ...hunt })
    .then((response) => {
      toastsStore.push(`Hunt "${response.name}" created.`, "success");
      reset();
      emit("created", response);
    })
    .catch((err) => (apiError.value = err?.message || String(err)));
}

function close() {
  reset();
  emit("close");
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1050;
}
.modal-card {
  width: 600px;
  max-width: calc(100% - 2rem);
}
</style>

<template>
  <div class="modal-backdrop" @click.self="close">
    <div class="modal-card">
      <div class="card">
        <div
          class="card-header d-flex justify-content-between align-items-center"
        >
          <strong>New Hunt</strong>
          <button type="button" class="btn-close" @click="close" />
        </div>

        <div class="card-body">
          <p class="text-muted small mb-3">
            A hunt runs a Lucene query against your indexed attributes or
            events, tracking how many matches are found each time.
          </p>

          <div class="mb-3">
            <label class="form-label" for="modal-hunt-name">Name</label>
            <input
              id="modal-hunt-name"
              class="form-control"
              v-model="hunt.name"
              placeholder="e.g. Suspicious IPs"
              autofocus
            />
          </div>

          <div class="mb-3">
            <label class="form-label" for="modal-hunt-description"
              >Description <span class="text-muted">(optional)</span></label
            >
            <textarea
              id="modal-hunt-description"
              class="form-control"
              rows="2"
              v-model="hunt.description"
              placeholder="What this hunt is looking for"
            />
          </div>

          <div class="mb-3">
            <label class="form-label" for="modal-hunt-target"
              >Search index</label
            >
            <select
              id="modal-hunt-target"
              class="form-select"
              v-model="hunt.index_target"
            >
              <option value="attributes">Attributes</option>
              <option value="events">Events</option>
              <option value="correlations">Correlations</option>
            </select>
          </div>

          <div class="mb-3">
            <label class="form-label" for="modal-hunt-query"
              >Lucene Query</label
            >
            <textarea
              id="modal-hunt-query"
              class="form-control font-monospace"
              rows="3"
              v-model="hunt.query"
              :placeholder="
                hunt.index_target === 'correlations'
                  ? 'e.g. target_attribute_value:192.168.1.1'
                  : 'e.g. type:ip-dst AND value:192.168.*'
              "
            />
            <div class="form-text text-muted d-flex gap-3">
              <div>
                <LuceneQuerySyntaxHint />
              </div>
              <div class="ms-auto">
                <AttributesPropertiesModal
                  v-if="hunt.index_target === 'attributes'"
                />
                <EventsPropertiesModal v-if="hunt.index_target === 'events'" />
                <CorrelationPropertiesModal
                  v-if="hunt.index_target === 'correlations'"
                />
              </div>
            </div>
          </div>

          <div class="mb-2">
            <div class="form-check form-switch">
              <input
                class="form-check-input"
                type="checkbox"
                role="switch"
                id="modal-hunt-active"
                :checked="hunt.status === 'active'"
                @change="
                  hunt.status = $event.target.checked ? 'active' : 'paused'
                "
              />
              <label class="form-check-label" for="modal-hunt-active"
                >Active</label
              >
            </div>
          </div>

          <div v-if="apiError" class="alert alert-danger mt-3 mb-0">
            {{ apiError }}
          </div>
        </div>

        <div class="card-footer d-flex justify-content-end gap-2">
          <button class="btn btn-outline-secondary" @click="close">
            Cancel
          </button>
          <button
            class="btn btn-primary"
            :disabled="!canSubmit || huntsStore.status.creating"
            @click="submit"
          >
            {{ huntsStore.status.creating ? "Creating…" : "Create Hunt" }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
