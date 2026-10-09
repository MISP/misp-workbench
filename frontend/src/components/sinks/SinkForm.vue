<script setup>
import { reactive, ref, computed } from "vue";
import { router } from "@/router";
import { useSinksStore, useToastsStore } from "@/stores";
import TagsSelect from "@/components/tags/TagsSelect.vue";

// With `sink` the form edits it; without, it creates a new one.
const props = defineProps({ sink: { type: Object, default: null } });

const sinksStore = useSinksStore();
const toastsStore = useToastsStore();

const TYPES = [
  { value: "splunk_hec", label: "Splunk HTTP Event Collector" },
  { value: "gelf", label: "Graylog GELF (TCP)" },
  { value: "syslog", label: "Syslog / CEF" },
  { value: "webhook", label: "Webhook (JSON)" },
];

const DEFAULT_CONFIG = {
  splunk_hec: {
    url: "",
    token: "",
    index: "",
    sourcetype: "misp:attribute",
    source: "misp-workbench",
    verify_tls: true,
    ca_cert: "",
  },
  gelf: { host: "", port: 12201, tls: false, verify_tls: true, ca_cert: "" },
  syslog: {
    host: "",
    port: 514,
    protocol: "udp",
    tls: false,
    verify_tls: true,
    ca_cert: "",
    hostname: "misp-workbench",
  },
  webhook: { url: "", secret: "", verify_tls: true, ca_cert: "" },
};

const isEdit = computed(() => props.sink !== null);

const form = reactive({
  name: props.sink?.name ?? "",
  type: props.sink?.type ?? "splunk_hec",
  enabled: props.sink?.enabled ?? true,
});

// One config per type, so switching type while creating keeps what was typed.
const configs = reactive(
  Object.fromEntries(
    Object.entries(DEFAULT_CONFIG).map(([type, defaults]) => [
      type,
      { ...defaults, ...(props.sink?.type === type ? props.sink.config : {}) },
    ]),
  ),
);
const config = computed(() => configs[form.type]);

const joinList = (list) => (list || []).join(", ");
const filters = reactive({
  to_ids_only: props.sink?.filters?.to_ids_only ?? true,
  types: joinList(props.sink?.filters?.types),
  // Tag names (or patterns such as tlp:*), edited with the tag selector.
  tags: [...(props.sink?.filters?.tags || [])],
  exclude_tags: props.sink
    ? [...(props.sink.filters?.exclude_tags || [])]
    : ["tlp:red"],
});

// TagsSelect works on tag objects; the sink stores plain names. Unknown names
// and patterns get a neutral colour, as in the retention settings.
const asTagObjects = (names) =>
  names.map((name) => ({ id: null, name, colour: "#6c757d" }));
const includeTagObjects = computed(() => asTagObjects(filters.tags));
const excludeTagObjects = computed(() => asTagObjects(filters.exclude_tags));

const apiError = ref(null);
const usesTls = computed(
  () =>
    ["splunk_hec", "webhook"].includes(form.type) ||
    (form.type === "gelf" && config.value.tls) ||
    (form.type === "syslog" && config.value.tls),
);

function splitList(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function cleanConfig() {
  // Empty optional fields go out as null rather than "".
  return Object.fromEntries(
    Object.entries(config.value).map(([key, value]) => [
      key,
      value === "" ? null : value,
    ]),
  );
}

async function submit() {
  apiError.value = null;
  const payload = {
    name: form.name,
    enabled: form.enabled,
    config: cleanConfig(),
    filters: {
      to_ids_only: filters.to_ids_only,
      types: splitList(filters.types),
      tags: filters.tags,
      exclude_tags: filters.exclude_tags,
    },
  };
  try {
    if (isEdit.value) {
      await sinksStore.update(props.sink.id, payload);
      toastsStore.push(`Sink "${form.name}" saved.`, "success");
    } else {
      await sinksStore.create({ ...payload, type: form.type });
      toastsStore.push(`Sink "${form.name}" created.`, "success");
    }
    router.push("/sinks");
  } catch (error) {
    apiError.value = error?.message || String(error);
  }
}
</script>

<template>
  <div class="card mx-auto" style="max-width: 720px">
    <div class="card-header border-bottom">
      <h4 class="mb-0">{{ isEdit ? "Edit Sink" : "New Sink" }}</h4>
    </div>
    <div class="card-body">
      <p class="text-muted mb-4">
        When an event is published, its indicators that pass the filters below
        are pushed to this destination. Deliveries are retried with backoff; the
        outcome shows in the sinks list.
      </p>

      <div class="mb-3">
        <label class="form-label" for="sink-name">Name</label>
        <input
          id="sink-name"
          class="form-control"
          v-model="form.name"
          placeholder="e.g. Splunk production"
        />
      </div>

      <div class="mb-3">
        <label class="form-label" for="sink-type">Type</label>
        <select
          id="sink-type"
          class="form-select"
          v-model="form.type"
          :disabled="isEdit"
        >
          <option v-for="t in TYPES" :key="t.value" :value="t.value">
            {{ t.label }}
          </option>
        </select>
      </div>

      <!-- ── destination ── -->
      <template v-if="form.type === 'splunk_hec' || form.type === 'webhook'">
        <div class="mb-3">
          <label class="form-label" for="sink-url">URL</label>
          <input
            id="sink-url"
            class="form-control font-monospace"
            v-model="config.url"
            :placeholder="
              form.type === 'splunk_hec'
                ? 'https://splunk.example.com:8088/services/collector/event'
                : 'https://hooks.example.com/misp'
            "
          />
        </div>
      </template>
      <template v-else>
        <div class="row g-3 mb-3">
          <div class="col-8">
            <label class="form-label" for="sink-host">Host</label>
            <input
              id="sink-host"
              class="form-control font-monospace"
              v-model="config.host"
              placeholder="graylog.example.com"
            />
          </div>
          <div class="col-4">
            <label class="form-label" for="sink-port">Port</label>
            <input
              id="sink-port"
              type="number"
              min="1"
              max="65535"
              class="form-control"
              v-model.number="config.port"
            />
          </div>
        </div>
      </template>

      <div v-if="form.type === 'splunk_hec'" class="row g-3 mb-3">
        <div class="col-12">
          <label class="form-label" for="sink-token">HEC token</label>
          <input
            id="sink-token"
            type="password"
            class="form-control font-monospace"
            v-model="config.token"
            autocomplete="off"
          />
          <div v-if="isEdit" class="form-text">
            Leave as is to keep the current token, unless you change the
            connection settings.
          </div>
        </div>
        <div class="col-4">
          <label class="form-label" for="sink-index">Index</label>
          <input
            id="sink-index"
            class="form-control"
            v-model="config.index"
            placeholder="default"
          />
        </div>
        <div class="col-4">
          <label class="form-label" for="sink-sourcetype">Sourcetype</label>
          <input
            id="sink-sourcetype"
            class="form-control"
            v-model="config.sourcetype"
          />
        </div>
        <div class="col-4">
          <label class="form-label" for="sink-source">Source</label>
          <input
            id="sink-source"
            class="form-control"
            v-model="config.source"
          />
        </div>
      </div>

      <div v-if="form.type === 'webhook'" class="mb-3">
        <label class="form-label" for="sink-secret">Signing secret</label>
        <input
          id="sink-secret"
          type="password"
          class="form-control font-monospace"
          v-model="config.secret"
          autocomplete="off"
        />
        <div class="form-text">
          Optional. Each request is then signed with an HMAC-SHA256 of its body
          in <code>X-Misp-Workbench-Signature</code>.
          <span v-if="isEdit"
            >Leave as is to keep the current secret, unless you change the
            connection settings.</span
          >
        </div>
      </div>

      <div v-if="form.type === 'syslog'" class="row g-3 mb-3">
        <div class="col-6">
          <label class="form-label" for="sink-protocol">Protocol</label>
          <select
            id="sink-protocol"
            class="form-select"
            v-model="config.protocol"
            @change="config.protocol === 'udp' && (config.tls = false)"
          >
            <option value="udp">UDP</option>
            <option value="tcp">TCP</option>
          </select>
        </div>
        <div class="col-6">
          <label class="form-label" for="sink-hostname">Syslog hostname</label>
          <input
            id="sink-hostname"
            class="form-control"
            v-model="config.hostname"
          />
        </div>
      </div>

      <div
        v-if="
          form.type === 'gelf' ||
          (form.type === 'syslog' && config.protocol === 'tcp')
        "
        class="form-check form-switch mb-3"
      >
        <input
          id="sink-tls"
          class="form-check-input"
          type="checkbox"
          v-model="config.tls"
        />
        <label class="form-check-label" for="sink-tls">Use TLS</label>
      </div>

      <template v-if="usesTls">
        <div class="mb-3">
          <label class="form-label" for="sink-ca">CA certificate (PEM)</label>
          <textarea
            id="sink-ca"
            class="form-control font-monospace small"
            rows="3"
            v-model="config.ca_cert"
            placeholder="-----BEGIN CERTIFICATE-----"
          />
          <div class="form-text">
            For a self-signed endpoint: verify it against its CA instead of
            turning verification off.
          </div>
        </div>
        <div class="form-check form-switch mb-3">
          <input
            id="sink-verify"
            class="form-check-input"
            type="checkbox"
            v-model="config.verify_tls"
          />
          <label class="form-check-label" for="sink-verify"
            >Verify TLS certificate</label
          >
          <div v-if="!config.verify_tls" class="form-text text-danger">
            Without verification, anyone able to intercept the connection can
            read and alter what is sent.
          </div>
        </div>
      </template>

      <!-- ── filters ── -->
      <hr />
      <h6 class="mb-3">What to send</h6>
      <div class="form-check form-switch mb-3">
        <input
          id="sink-to-ids"
          class="form-check-input"
          type="checkbox"
          v-model="filters.to_ids_only"
        />
        <label class="form-check-label" for="sink-to-ids"
          >Only attributes flagged for IDS</label
        >
      </div>
      <div class="mb-3">
        <label class="form-label" for="sink-types">Attribute types</label>
        <input
          id="sink-types"
          class="form-control font-monospace"
          v-model="filters.types"
          placeholder="all types — or e.g. ip-src, ip-dst, domain, url"
        />
      </div>
      <div class="mb-3">
        <label class="form-label">Only with tags</label>
        <!-- persist=false: only edits this list, never tags an event -->
        <TagsSelect
          modelClass="event"
          :persist="false"
          :selectedTags="includeTagObjects"
          @update:selectedTags="filters.tags = $event"
        />
        <div class="form-text">Empty sends attributes with any tags.</div>
      </div>
      <div class="mb-3">
        <label class="form-label">Never with tags</label>
        <TagsSelect
          modelClass="event"
          :persist="false"
          :selectedTags="excludeTagObjects"
          @update:selectedTags="filters.exclude_tags = $event"
        />
        <div class="form-text">
          Both lists match attribute and event tags alike. Type a pattern such
          as <code>tlp:*</code> to match a whole namespace.
        </div>
      </div>

      <div class="form-check form-switch mb-4">
        <input
          id="sink-enabled"
          class="form-check-input"
          type="checkbox"
          v-model="form.enabled"
        />
        <label class="form-check-label" for="sink-enabled">Enabled</label>
      </div>

      <div v-if="apiError" class="alert alert-danger">{{ apiError }}</div>

      <div class="d-flex justify-content-end gap-2">
        <button
          class="btn btn-outline-secondary"
          @click="router.push('/sinks')"
        >
          Cancel
        </button>
        <button
          class="btn btn-primary"
          :disabled="!form.name || sinksStore.status.saving"
          @click="submit"
        >
          {{ sinksStore.status.saving ? "Saving…" : "Save" }}
        </button>
      </div>
    </div>
  </div>
</template>
