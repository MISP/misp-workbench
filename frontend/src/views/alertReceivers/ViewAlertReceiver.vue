<script setup>
import { ref, computed } from "vue";
import { storeToRefs } from "pinia";
import { useAlertReceiversStore, useAuthStore, useToastsStore } from "@/stores";
import { authHelper } from "@/helpers";
import { router } from "@/router";
import Spinner from "@/components/misc/Spinner.vue";
import Timestamp from "@/components/misc/Timestamp.vue";
import CopyToClipboard from "@/components/misc/CopyToClipboard.vue";
import AlertReceiverFormModal from "@/components/alertReceivers/AlertReceiverFormModal.vue";

const props = defineProps({ id: { type: [String, Number], required: true } });

const receiversStore = useAlertReceiversStore();
const toastsStore = useToastsStore();
const { presetsById } = storeToRefs(receiversStore);
const { scopes } = storeToRefs(useAuthStore());
const canManage = computed(
  () =>
    authHelper.hasScope(scopes.value, "alert_receivers:manage") &&
    authHelper.hasScope(scopes.value, "sightings:create"),
);

// The console tells which values attributes hold.
const canTry = computed(() =>
  authHelper.hasScope(scopes.value, "attributes:read"),
);

const FIELDS = [
  [
    "records",
    "Records",
    "The alerts in a request. @: the body, or each element of an array.",
  ],
  ["values", "Values", "The values an alert hit: a string, or arrays of them."],
  [
    "type",
    "Type",
    "positive, false-positive or expiration (MISP's 0, 1, 2). Empty: positive.",
  ],
  [
    "source",
    "Source",
    "The rule or sensor that raised it. Empty: this webhook's name.",
  ],
  [
    "timestamp",
    "Timestamp",
    "Epoch seconds or milliseconds, or ISO 8601. Empty: when it arrives.",
  ],
  [
    "attribute_uuid",
    "Attribute uuid",
    "An attribute's uuid: the alert sights that attribute.",
  ],
];

const receiver = ref(null);
const error = ref(null);
const mapping = ref({});
const savingMapping = ref(false);
// The receiver's URL, when its token was just created: shown this once.
const fresh = ref(null);

function loaded(value) {
  receiver.value = value;
  mapping.value = { ...value.mapping };
}

async function load() {
  try {
    loaded(await receiversStore.get(props.id));
    if (receiversStore.fresh?.id === receiver.value.id) {
      fresh.value = receiversStore.fresh.url;
      receiversStore.fresh = null;
    }
  } catch (err) {
    error.value = err;
  }
}
load();
receiversStore.getPresets().catch(() => {});

const preset = computed(() => presetsById.value[receiver.value?.preset]);
const mappingChanged = computed(
  () =>
    receiver.value &&
    FIELDS.some(
      ([key]) =>
        (mapping.value[key] || null) !== (receiver.value.mapping[key] || null),
    ),
);

async function saveMapping() {
  savingMapping.value = true;
  try {
    const cleaned = Object.fromEntries(
      FIELDS.map(([key]) => [key, mapping.value[key]?.trim() || null]),
    );
    loaded(await receiversStore.update(props.id, { mapping: cleaned }));
    toastsStore.push("Mapping saved.", "success");
  } catch (err) {
    toastsStore.push(`${err}`, "danger");
  } finally {
    savingMapping.value = false;
  }
}

function presetMapping() {
  if (preset.value) mapping.value = { ...preset.value.mapping };
}

async function rotate() {
  if (
    !confirm(
      `A new URL for "${receiver.value.name}"? The current one stops working at once: update its senders.`,
    )
  )
    return;
  try {
    const rotated = await receiversStore.rotateToken(props.id);
    fresh.value = receiversStore.urlOf(rotated.path);
    loaded(await receiversStore.get(props.id));
  } catch (err) {
    toastsStore.push(`${err}`, "danger");
  }
}

async function remove() {
  if (
    !confirm(
      `Delete "${receiver.value.name}"? Its senders get a 404 from now on; the sightings it reported stay.`,
    )
  )
    return;
  try {
    await receiversStore.remove(props.id);
    toastsStore.push(`"${receiver.value.name}" deleted.`, "success");
    router.push("/alert-receivers");
  } catch (err) {
    toastsStore.push(`${err}`, "danger");
  }
}

function saved(updated) {
  loaded(updated);
  toastsStore.push(`"${updated.name}" saved.`, "success");
}

// Test console
const sample = ref("");
const result = ref(null);
const testing = ref(false);
const sampleError = ref(null);

function useSample() {
  if (preset.value) sample.value = JSON.stringify(preset.value.sample, null, 2);
}

async function useLast() {
  try {
    const last = await receiversStore.lastPayload(props.id);
    if (!last.payload) {
      toastsStore.push("Nothing received yet.", "info");
      return;
    }
    try {
      sample.value = JSON.stringify(JSON.parse(last.payload), null, 2);
    } catch {
      sample.value = last.payload;
    }
  } catch (err) {
    toastsStore.push(`${err}`, "danger");
  }
}

async function tryMapping() {
  sampleError.value = null;
  result.value = null;
  let payload;
  try {
    payload = JSON.parse(sample.value);
  } catch (err) {
    sampleError.value = `That's no JSON: ${err.message}`;
    return;
  }
  testing.value = true;
  try {
    const cleaned = Object.fromEntries(
      FIELDS.map(([key]) => [key, mapping.value[key]?.trim() || null]),
    );
    result.value = await receiversStore.test(
      cleaned,
      payload,
      receiver.value.only_known,
      receiver.value.name,
    );
  } catch (err) {
    sampleError.value = `${err}`;
  } finally {
    testing.value = false;
  }
}
</script>

<template>
  <div v-if="error" class="alert alert-danger">{{ error }}</div>
  <Spinner v-else-if="!receiver" />
  <div v-else>
    <div class="card mb-3">
      <div
        class="card-header border-bottom d-flex justify-content-between align-items-center flex-wrap gap-2"
      >
        <h4 class="mb-0">
          {{ receiver.name }}
          <span v-if="!receiver.enabled" class="badge text-bg-secondary ms-2"
            >disabled</span
          >
        </h4>
        <div v-if="canManage" class="d-flex gap-2">
          <button
            type="button"
            class="btn btn-outline-secondary btn-sm"
            title="A new URL; the current one stops working"
            @click="rotate"
          >
            New URL
          </button>
          <button
            type="button"
            class="btn btn-outline-primary btn-sm"
            data-bs-toggle="modal"
            data-bs-target="#alertReceiverEditModal"
          >
            Edit
          </button>
          <button
            type="button"
            class="btn btn-outline-danger btn-sm"
            @click="remove"
          >
            Delete
          </button>
        </div>
      </div>
      <div class="card-body">
        <p v-if="receiver.description" class="text-muted">
          {{ receiver.description }}
        </p>
        <div v-if="fresh" class="alert alert-success" id="receiver-fresh-url">
          <div class="fw-semibold mb-1">
            The URL to post to, shown this once:
          </div>
          <div class="d-flex align-items-center">
            <code class="text-break flex-grow-1">{{ fresh }}</code>
            <CopyToClipboard :value="fresh" />
          </div>
          <div class="small mt-1">
            Only its hash is kept: put it in the sender's webhook settings now.
            If you lose it, get a new URL.
          </div>
        </div>
        <dl class="row mb-0">
          <dt class="col-sm-3">Sender</dt>
          <dd class="col-sm-9">{{ preset?.name ?? receiver.preset }}</dd>
          <dt class="col-sm-3">URL</dt>
          <dd class="col-sm-9 font-monospace small">
            …/webhooks/alerts/{{ receiver.token_prefix }}…
          </dd>
          <dt class="col-sm-3">Reports</dt>
          <dd class="col-sm-9">
            {{
              receiver.only_known
                ? "values an attribute holds"
                : "every value an alert carries"
            }}
          </dd>
          <dt class="col-sm-3">Takes</dt>
          <dd class="col-sm-9">
            at most {{ receiver.rate_limit.toLocaleString() }} requests a
            minute, from
            <span class="font-monospace small">{{
              receiver.allowed_ips.join(", ") || "anywhere"
            }}</span>
          </dd>
          <dt class="col-sm-3">Received</dt>
          <dd class="col-sm-9">
            {{ receiver.received_count.toLocaleString() }} requests,
            {{ receiver.sightings_count.toLocaleString() }} sightings
            <template v-if="receiver.last_received_at">
              · last
              <Timestamp :timestamp="receiver.last_received_at" />
              <span class="text-muted font-monospace small">
                from {{ receiver.last_ip }}</span
              >
            </template>
            <div v-if="receiver.last_error" class="text-danger small">
              The last request was refused:
              {{ receiver.last_error }}. Nothing in it was reported.
            </div>
          </dd>
        </dl>
      </div>
    </div>

    <div v-if="preset" class="card mb-3">
      <div class="card-header border-bottom">
        <h5 class="mb-0">Setting up {{ preset.name }}</h5>
      </div>
      <div class="card-body">
        <p class="mb-0" id="receiver-setup">{{ preset.setup }}</p>
      </div>
    </div>

    <div class="row g-3">
      <div class="col-lg-6">
        <div class="card h-100">
          <div
            class="card-header border-bottom d-flex justify-content-between align-items-center"
          >
            <h5 class="mb-0">Mapping</h5>
            <div v-if="canManage" class="d-flex gap-2">
              <button
                type="button"
                class="btn btn-outline-secondary btn-sm"
                :disabled="!preset"
                @click="presetMapping"
              >
                The sender's
              </button>
              <button
                type="button"
                class="btn btn-primary btn-sm"
                :disabled="!mappingChanged || savingMapping"
                @click="saveMapping"
              >
                {{ savingMapping ? "Saving…" : "Save" }}
              </button>
            </div>
          </div>
          <div class="card-body">
            <p class="text-muted small">
              <a href="https://jmespath.org/tutorial.html" target="_blank"
                >JMESPath</a
              >
              expressions, read from each record; <code>root()</code> is the
              whole body. A request the mapping can't read is refused whole.
            </p>
            <div v-for="[key, label, help] in FIELDS" :key="key" class="mb-2">
              <label class="form-label small mb-0" :for="`mapping-${key}`">{{
                label
              }}</label>
              <input
                :id="`mapping-${key}`"
                v-model="mapping[key]"
                class="form-control form-control-sm font-monospace"
                :readonly="!canManage"
              />
              <div class="form-text mt-0">{{ help }}</div>
            </div>
          </div>
        </div>
      </div>
      <div v-if="canTry" class="col-lg-6">
        <div class="card h-100">
          <div
            class="card-header border-bottom d-flex justify-content-between align-items-center"
          >
            <h5 class="mb-0">Try it</h5>
            <div class="d-flex gap-2">
              <button
                type="button"
                class="btn btn-outline-secondary btn-sm"
                :disabled="!preset"
                @click="useSample"
              >
                Sample
              </button>
              <button
                v-if="canManage"
                type="button"
                class="btn btn-outline-secondary btn-sm"
                :disabled="!receiver.last_received_at"
                @click="useLast"
              >
                Last received
              </button>
            </div>
          </div>
          <div class="card-body">
            <p class="text-muted small">
              Paste a body as the sender posts it: what the mapping above, saved
              or not, reads out of it. Nothing is reported.
            </p>
            <textarea
              v-model="sample"
              id="receiver-sample"
              class="form-control font-monospace small mb-2"
              rows="10"
              placeholder='{"result": {"dest_ip": "185.220.101.42"}}'
            ></textarea>
            <button
              type="button"
              class="btn btn-primary btn-sm mb-3"
              :disabled="!sample.trim() || testing"
              @click="tryMapping"
            >
              {{ testing ? "Reading…" : "Read it" }}
            </button>
            <div v-if="sampleError" class="alert alert-danger small">
              {{ sampleError }}
            </div>
            <div v-if="result" id="receiver-result">
              <div v-if="result.error" class="alert alert-danger small">
                Refused: {{ result.error }}
              </div>
              <template v-else>
                <p class="small mb-2">
                  {{ result.records }}
                  {{ result.records === 1 ? "record" : "records" }},
                  {{ result.sightings.length }}
                  {{ result.sightings.length === 1 ? "sighting" : "sightings" }}
                  <span v-if="result.skipped" class="text-muted"
                    >· {{ result.skipped }} left out, no attribute holding
                    them</span
                  >
                </p>
                <div class="table-responsive">
                  <table class="table table-sm small align-middle mb-0">
                    <thead>
                      <tr>
                        <th>value</th>
                        <th>type</th>
                        <th>source</th>
                        <th>seen</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="(s, i) in result.sightings"
                        :key="`${s.value}-${i}`"
                      >
                        <td class="font-monospace text-break">
                          {{ s.value }}
                          <span
                            v-if="!s.known"
                            class="badge text-bg-light border ms-1"
                            title="No attribute holds it"
                            >unknown</span
                          >
                        </td>
                        <td>{{ s.type }}</td>
                        <td>{{ s.source }}</td>
                        <td><Timestamp :timestamp="s.timestamp" /></td>
                      </tr>
                      <tr v-if="!result.sightings.length">
                        <td colspan="4" class="text-muted">
                          Nothing to report.
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>
    </div>
    <AlertReceiverFormModal
      v-if="canManage"
      modal-id="alertReceiverEditModal"
      :receiver="receiver"
      @saved="saved"
    />
  </div>
</template>
