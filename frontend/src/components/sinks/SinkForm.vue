<script setup>
import { reactive, ref, computed } from "vue";
import { router } from "@/router";
import {
  useSinksStore,
  useToastsStore,
  useDetectionProfilesStore,
} from "@/stores";
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
  { value: "sentinel", label: "Microsoft Sentinel (threat intelligence)" },
  { value: "defender", label: "Microsoft Defender for Endpoint (indicators)" },
  { value: "elastic", label: "Elastic Security (threat indicators)" },
];
// Platforms taking indicators through their own APIs.
const VENDOR_TYPES = ["sentinel", "defender", "elastic"];

const ENTRA_APP = {
  tenant_id: "",
  client_id: "",
  client_secret: "",
  login_url: "https://login.microsoftonline.com",
  verify_tls: true,
  ca_cert: "",
};

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
  sentinel: {
    ...ENTRA_APP,
    workspace_id: "",
    source_system: "misp-workbench",
    valid_days: 30,
    api_url: "https://api.ti.sentinel.azure.com",
    api_version: "2024-02-01-preview",
    scope: "https://management.azure.com/.default",
  },
  defender: {
    ...ENTRA_APP,
    action: "alert",
    expiry_days: 30,
    application: "misp-workbench",
    rbac_group_names: "",
    api_url: "https://api.security.microsoft.com",
    scope: "https://api.securitycenter.microsoft.com/.default",
  },
  elastic: {
    url: "",
    index: "misp-workbench-indicators",
    api_key: "",
    username: "",
    password: "",
    verify_tls: true,
    ca_cert: "",
  },
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
// Edited as a comma-separated list.
configs.defender.rbac_group_names = []
  .concat(configs.defender.rbac_group_names || [])
  .join(", ");
const isVendor = computed(() => VENDOR_TYPES.includes(form.type));
const showAdvanced = ref(false);
const config = computed(() => configs[form.type]);

const joinList = (list) => (list || []).join(", ");
const profilesStore = useDetectionProfilesStore();
profilesStore.getAll();

const filters = reactive({
  to_ids_only: props.sink?.filters?.to_ids_only ?? true,
  exclude_warninglisted: props.sink?.filters?.exclude_warninglisted ?? true,
  indicator_mode: props.sink?.filters?.indicator_mode ?? false,
  min_score: props.sink?.filters?.min_score ?? 0,
  profile_id: props.sink?.filters?.profile_id ?? null,
  sync_membership: props.sink?.filters?.sync_membership ?? false,
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
    ["splunk_hec", "webhook", ...VENDOR_TYPES].includes(form.type) ||
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
  const cleaned = Object.fromEntries(
    Object.entries(config.value).map(([key, value]) => [
      key,
      value === "" ? null : value,
    ]),
  );
  if (form.type === "defender") {
    cleaned.rbac_group_names = splitList(config.value.rbac_group_names || "");
  }
  return cleaned;
}

async function submit() {
  apiError.value = null;
  const payload = {
    name: form.name,
    enabled: form.enabled,
    config: cleanConfig(),
    filters: {
      to_ids_only: filters.to_ids_only,
      exclude_warninglisted: filters.exclude_warninglisted,
      indicator_mode: filters.indicator_mode,
      min_score: filters.min_score || 0,
      profile_id: filters.profile_id,
      sync_membership: !!filters.profile_id && filters.sync_membership,
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
        <label class="form-label" for="sink-type"
          >Type
          <span v-if="isVendor" class="badge text-bg-warning ms-1"
            >beta</span
          ></label
        >
        <select
          id="sink-type"
          class="form-select"
          v-model="form.type"
          :disabled="isEdit"
        >
          <option v-for="t in TYPES" :key="t.value" :value="t.value">
            {{ t.label }}{{ VENDOR_TYPES.includes(t.value) ? " — beta" : "" }}
          </option>
        </select>
        <div v-if="isVendor" class="form-text">
          Beta: this sink is new. It follows the vendor's documented API but
          hasn't been run against every live tenant yet; check what it delivers
          before relying on it, and report what doesn't work.
        </div>
      </div>

      <!-- ── destination ── -->
      <template
        v-if="
          form.type === 'splunk_hec' ||
          form.type === 'webhook' ||
          form.type === 'elastic'
        "
      >
        <div class="mb-3">
          <label class="form-label" for="sink-url">URL</label>
          <input
            id="sink-url"
            class="form-control font-monospace"
            v-model="config.url"
            :placeholder="
              form.type === 'splunk_hec'
                ? 'https://splunk.example.com:8088/services/collector/event'
                : form.type === 'elastic'
                  ? 'https://elastic.example.com:9200'
                  : 'https://hooks.example.com/misp'
            "
          />
        </div>
      </template>
      <template v-else-if="!isVendor">
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

      <!-- ── Microsoft (Entra ID app) ── -->
      <template v-if="form.type === 'sentinel' || form.type === 'defender'">
        <p class="form-text mt-0">
          An Entra ID app registration with a client secret.
          <template v-if="form.type === 'sentinel'"
            >Give it the <strong>Microsoft Sentinel Contributor</strong> role on
            the workspace.</template
          >
          <template v-else
            >Give it the <strong>WindowsDefenderATP</strong> application
            permission <code>Ti.ReadWrite.All</code>, with admin
            consent.</template
          >
        </p>
        <div class="row g-3 mb-3">
          <div class="col-md-6">
            <label class="form-label" for="sink-tenant">Tenant ID</label>
            <input
              id="sink-tenant"
              class="form-control font-monospace"
              v-model="config.tenant_id"
              placeholder="contoso.onmicrosoft.com or its GUID"
            />
          </div>
          <div class="col-md-6">
            <label class="form-label" for="sink-client">Client ID</label>
            <input
              id="sink-client"
              class="form-control font-monospace"
              v-model="config.client_id"
            />
          </div>
          <div class="col-12">
            <label class="form-label" for="sink-client-secret"
              >Client secret</label
            >
            <input
              id="sink-client-secret"
              type="password"
              class="form-control font-monospace"
              v-model="config.client_secret"
              autocomplete="off"
            />
            <div v-if="isEdit" class="form-text">
              Leave as is to keep the current secret, unless you change the
              tenant, app or endpoints.
            </div>
          </div>
        </div>
      </template>

      <div v-if="form.type === 'sentinel'" class="row g-3 mb-3">
        <div class="col-md-6">
          <label class="form-label" for="sink-workspace">Workspace ID</label>
          <input
            id="sink-workspace"
            class="form-control font-monospace"
            v-model="config.workspace_id"
            placeholder="00000000-0000-0000-0000-000000000000"
          />
        </div>
        <div class="col-md-3">
          <label class="form-label" for="sink-source-system"
            >Source system</label
          >
          <input
            id="sink-source-system"
            class="form-control"
            v-model="config.source_system"
          />
        </div>
        <div class="col-md-3">
          <label class="form-label" for="sink-valid-days">Valid (days)</label>
          <input
            id="sink-valid-days"
            type="number"
            min="1"
            max="365"
            class="form-control"
            v-model.number="config.valid_days"
          />
        </div>
        <div class="col-12 form-text mt-1">
          STIX indicators, with the score as confidence and the TLP as marking.
          Each stays valid for this many days after its value was last seen; one
          that leaves the profile is expired.
        </div>
      </div>

      <div v-if="form.type === 'defender'" class="row g-3 mb-3">
        <div class="col-md-4">
          <label class="form-label" for="sink-action">Action</label>
          <select id="sink-action" class="form-select" v-model="config.action">
            <option value="audit">Audit only</option>
            <option value="alert">Alert</option>
            <option value="block">Block and alert</option>
          </select>
        </div>
        <div class="col-md-4">
          <label class="form-label" for="sink-expiry-days"
            >Expires (days)</label
          >
          <input
            id="sink-expiry-days"
            type="number"
            min="1"
            max="365"
            class="form-control"
            v-model.number="config.expiry_days"
          />
        </div>
        <div class="col-md-4">
          <label class="form-label" for="sink-application">Application</label>
          <input
            id="sink-application"
            class="form-control"
            v-model="config.application"
          />
        </div>
        <div class="col-12">
          <label class="form-label" for="sink-rbac">Device groups</label>
          <input
            id="sink-rbac"
            class="form-control"
            v-model="config.rbac_group_names"
            placeholder="all devices — or e.g. Servers, Workstations"
          />
        </div>
        <div class="col-12 form-text mt-1">
          Addresses must be single and public: Defender takes no networks, and a
          private address would match your own hosts. Severity follows the
          score. Each indicator expires this many days after its value was last
          seen; removals delete only indicators carrying this application name.
          Defender holds at most 15,000 indicators per tenant: send it a
          profile.
        </div>
      </div>

      <div v-if="form.type === 'elastic'" class="row g-3 mb-3">
        <div class="col-md-6">
          <label class="form-label" for="sink-es-index">Index</label>
          <input
            id="sink-es-index"
            class="form-control font-monospace"
            v-model="config.index"
          />
        </div>
        <div class="col-md-6">
          <label class="form-label" for="sink-api-key">API key</label>
          <input
            id="sink-api-key"
            type="password"
            class="form-control font-monospace"
            v-model="config.api_key"
            autocomplete="off"
            placeholder="the encoded key"
          />
        </div>
        <div class="col-md-6">
          <label class="form-label" for="sink-es-user">Or username</label>
          <input
            id="sink-es-user"
            class="form-control"
            v-model="config.username"
            autocomplete="off"
          />
        </div>
        <div class="col-md-6">
          <label class="form-label" for="sink-es-password">Password</label>
          <input
            id="sink-es-password"
            type="password"
            class="form-control"
            v-model="config.password"
            autocomplete="off"
          />
        </div>
        <div class="col-12 form-text mt-1">
          ECS <code>threat.indicator.*</code> documents, one per value, for
          Elastic Security's indicator match rules (add the index to the rule's
          indicator index patterns). The index is created with ECS field types
          if it doesn't exist. The key needs <code>create_index</code>,
          <code>index</code> and <code>delete</code> on it.
          <span v-if="isEdit"
            >Leave the key and password as they are to keep them, unless you
            change the URL.</span
          >
        </div>
      </div>

      <template v-if="form.type === 'sentinel' || form.type === 'defender'">
        <button
          type="button"
          class="btn btn-link btn-sm px-0 mb-2"
          @click="showAdvanced = !showAdvanced"
        >
          {{ showAdvanced ? "Hide" : "Show" }} endpoints
        </button>
        <div v-if="showAdvanced" class="row g-3 mb-3">
          <div class="col-12 form-text mt-0">
            For sovereign clouds (US Government, China). The defaults are
            Microsoft's commercial cloud.
          </div>
          <div class="col-md-6">
            <label class="form-label" for="sink-login-url">Login URL</label>
            <input
              id="sink-login-url"
              class="form-control font-monospace"
              v-model="config.login_url"
            />
          </div>
          <div class="col-md-6">
            <label class="form-label" for="sink-api-url">API URL</label>
            <input
              id="sink-api-url"
              class="form-control font-monospace"
              v-model="config.api_url"
            />
          </div>
          <div class="col-md-8">
            <label class="form-label" for="sink-scope">Token scope</label>
            <input
              id="sink-scope"
              class="form-control font-monospace"
              v-model="config.scope"
            />
          </div>
          <div v-if="form.type === 'sentinel'" class="col-md-4">
            <label class="form-label" for="sink-api-version">API version</label>
            <input
              id="sink-api-version"
              class="form-control font-monospace"
              v-model="config.api_version"
            />
          </div>
        </div>
      </template>

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
      <div class="mb-3">
        <label class="form-label" for="sink-profile">Detection profile</label>
        <select
          id="sink-profile"
          class="form-select"
          v-model="filters.profile_id"
        >
          <option :value="null">None: use the filters below</option>
          <option v-for="p in profilesStore.profiles" :key="p.id" :value="p.id">
            {{ p.name }} ({{ p.granularity }})
          </option>
        </select>
        <div class="form-text">
          A profile replaces every filter: its rules select what is sent, and it
          sends either attributes or consolidated indicators.
        </div>
      </div>
      <div v-if="filters.profile_id" class="form-check form-switch mb-3">
        <input
          id="sink-sync-membership"
          class="form-check-input"
          type="checkbox"
          v-model="filters.sync_membership"
        />
        <label class="form-check-label" for="sink-sync-membership"
          >Keep in step with the profile</label
        >
        <div class="form-text">
          Every few minutes, send what joined the profile and what left it
          (<code>action: remove</code>, with the reason), instead of each
          published event. The first sync sends every member. Needs a profile of
          indicators.
        </div>
      </div>
      <template v-if="!filters.profile_id">
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
        <div class="form-check form-switch mb-3">
          <input
            id="sink-indicator-mode"
            class="form-check-input"
            type="checkbox"
            v-model="filters.indicator_mode"
          />
          <label class="form-check-label" for="sink-indicator-mode"
            >Send consolidated indicators</label
          >
          <div class="form-text">
            One record per value, with its sources, first and last seen,
            sightings and the tags of every event it is in. Tag exclusions then
            judge the value: one that is <code>tlp:red</code> anywhere is left
            out.
          </div>
        </div>
        <div class="mb-3">
          <label class="form-label" for="sink-min-score">Minimum score</label>
          <input
            id="sink-min-score"
            class="form-control"
            type="number"
            min="0"
            max="100"
            v-model.number="filters.min_score"
            style="max-width: 10em"
          />
          <div class="form-text">
            Leave out values whose indicator's confidence (0–100, from sources,
            age, sightings and warninglists) is below this. 0 sends regardless;
            values too new to be scored are sent.
          </div>
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
      </template>
      <p v-if="filters.profile_id" class="form-text">
        The sink's own exclusions below still hold on top of the profile.
      </p>
      <div class="form-check form-switch mb-3">
        <input
          id="sink-warninglisted"
          class="form-check-input"
          type="checkbox"
          v-model="filters.exclude_warninglisted"
        />
        <label class="form-check-label" for="sink-warninglisted"
          >Leave out values on an enabled warninglist</label
        >
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
