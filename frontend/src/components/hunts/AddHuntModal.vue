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
  hunt_type: "opensearch",
  index_target: props.initialIndexTarget,
  status: "active",
});

const apiError = ref(null);

const canSubmit = computed(() => hunt.name && hunt.query);

function reset() {
  hunt.name = "";
  hunt.description = "";
  hunt.query = props.initialQuery;
  hunt.hunt_type = "opensearch";
  hunt.index_target = props.initialIndexTarget;
  hunt.status = "active";
  apiError.value = null;
}

function onHuntTypeChange() {
  if (hunt.hunt_type === "mitre-attack-pattern") {
    if (
      !["attributes", "events", "attributes_and_events"].includes(
        hunt.index_target,
      )
    ) {
      hunt.index_target = "attributes_and_events";
    }
  } else if (hunt.hunt_type === "opensearch") {
    if (hunt.index_target === "attributes_and_events") {
      hunt.index_target = "attributes";
    }
  }
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
            A hunt periodically checks for new matches and notifies you when the
            count changes.
          </p>

          <div class="mb-3">
            <label class="form-label">Hunt Type</label>
            <div class="d-flex gap-3">
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="radio"
                  id="modal-type-opensearch"
                  value="opensearch"
                  v-model="hunt.hunt_type"
                  @change="onHuntTypeChange"
                />
                <label class="form-check-label" for="modal-type-opensearch"
                  >OpenSearch query</label
                >
              </div>
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="radio"
                  id="modal-type-rulezet"
                  value="rulezet"
                  v-model="hunt.hunt_type"
                  @change="onHuntTypeChange"
                />
                <label class="form-check-label" for="modal-type-rulezet"
                  >Rulezet Vuln check</label
                >
              </div>
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="radio"
                  id="modal-type-cpe"
                  value="cpe"
                  v-model="hunt.hunt_type"
                  @change="onHuntTypeChange"
                />
                <label class="form-check-label" for="modal-type-cpe"
                  >CPE Vuln lookup</label
                >
              </div>
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="radio"
                  id="modal-type-mitre"
                  value="mitre-attack-pattern"
                  v-model="hunt.hunt_type"
                  @change="onHuntTypeChange"
                />
                <label class="form-check-label" for="modal-type-mitre"
                  >MITRE ATT&amp;CK pattern</label
                >
              </div>
            </div>
          </div>

          <div class="mb-3">
            <label class="form-label" for="modal-hunt-name">Name</label>
            <input
              id="modal-hunt-name"
              class="form-control"
              v-model="hunt.name"
              :placeholder="
                hunt.hunt_type === 'opensearch'
                  ? 'e.g. Suspicious IPs'
                  : hunt.hunt_type === 'rulezet'
                    ? 'e.g. SharePoint RCE CVEs'
                    : hunt.hunt_type === 'cpe'
                      ? 'e.g. GitLab Vulns'
                      : 'Hunt Name'
              "
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

          <template v-if="hunt.hunt_type === 'opensearch'">
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
                  <EventsPropertiesModal
                    v-if="hunt.index_target === 'events'"
                  />
                  <CorrelationPropertiesModal
                    v-if="hunt.index_target === 'correlations'"
                  />
                </div>
              </div>
            </div>
          </template>

          <div v-else-if="hunt.hunt_type === 'rulezet'" class="mb-3">
            <label class="form-label" for="modal-hunt-cve">Vuln ID</label>
            <input
              id="modal-hunt-cve"
              class="form-control font-monospace"
              v-model="hunt.query"
              placeholder="e.g. CVE-2024-1234"
            />
          </div>

          <div v-else-if="hunt.hunt_type === 'cpe'" class="mb-3">
            <label class="form-label" for="modal-hunt-cpe">CPE string</label>
            <input
              id="modal-hunt-cpe"
              class="form-control font-monospace"
              v-model="hunt.query"
              placeholder="cpe:/a:gitlab:gitlab"
            />
            <div class="form-text">
              Queries vulnerability.circl.lu for CVEs affecting this CPE.
              Notifies you when the result set changes.
            </div>
          </div>

          <template v-else-if="hunt.hunt_type === 'mitre-attack-pattern'">
            <div class="mb-3">
              <label class="form-label" for="modal-hunt-mitre-target"
                >Search index</label
              >
              <select
                id="modal-hunt-mitre-target"
                class="form-select"
                v-model="hunt.index_target"
              >
                <option value="attributes_and_events">
                  Attributes &amp; Events
                </option>
                <option value="events">Events</option>
                <option value="attributes">Attributes</option>
              </select>
            </div>

            <div class="mb-3">
              <label class="form-label" for="modal-hunt-mitre"
                >MITRE ATT&amp;CK technique</label
              >
              <textarea
                id="modal-hunt-mitre"
                class="form-control font-monospace"
                rows="3"
                v-model="hunt.query"
                placeholder="T1391, T1078.004"
              />
              <div class="form-text">
                MITRE ATT&amp;CK technique codes (e.g. <code>T1391</code>,
                <code>T1078.004</code>), comma or newline separated.
              </div>
            </div>
          </template>

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
