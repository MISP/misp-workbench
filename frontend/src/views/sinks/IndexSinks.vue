<script setup>
import { ref, computed } from "vue";
import { storeToRefs } from "pinia";
import { router } from "@/router";
import { useSinksStore, useAuthStore, useToastsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";
import { authHelper } from "@/helpers";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const sinksStore = useSinksStore();
const authStore = useAuthStore();
const toastsStore = useToastsStore();
const { sinks, status } = storeToRefs(sinksStore);
const { scopes } = storeToRefs(authStore);

const can = (scope) =>
  computed(() => authHelper.hasScope(scopes.value, `sinks:${scope}`));
const canCreate = can("create");
const canUpdate = can("update");
const canDelete = can("delete");
const canTest = can("test");

const TYPE_LABELS = {
  splunk_hec: "Splunk HEC",
  gelf: "GELF",
  syslog: "Syslog/CEF",
  webhook: "Webhook",
};

const testingId = ref(null);
const togglingId = ref(null);

sinksStore.getAll();

function destination(sink) {
  const c = sink.config || {};
  if (c.url) return c.url;
  const proto = sink.type === "syslog" ? `/${c.protocol}` : "";
  return `${c.host}:${c.port}${proto}${c.tls ? " (TLS)" : ""}`;
}

function filtersSummary(filters) {
  const parts = [];
  if (filters?.to_ids_only) parts.push("IDS only");
  if (filters?.types?.length) parts.push(filters.types.join(", "));
  if (filters?.tags?.length) parts.push(`tags: ${filters.tags.join(", ")}`);
  if (filters?.exclude_tags?.length)
    parts.push(`not: ${filters.exclude_tags.join(", ")}`);
  return parts.join(" · ") || "everything";
}

function since(timestamp) {
  return timestamp ? dayjs.utc(timestamp).local().fromNow() : null;
}

// The last attempt failed when its error is at least as recent as its success.
function failing(sink) {
  return (
    sink.last_error_at &&
    (!sink.last_success_at ||
      dayjs(sink.last_error_at).isAfter(dayjs(sink.last_success_at)))
  );
}

async function toggleEnabled(sink) {
  togglingId.value = sink.id;
  try {
    await sinksStore.update(sink.id, { enabled: !sink.enabled });
    await sinksStore.getAll();
  } catch (error) {
    toastsStore.push(`Could not update "${sink.name}": ${error}`, "danger");
  } finally {
    togglingId.value = null;
  }
}

async function sendTest(sink) {
  testingId.value = sink.id;
  try {
    const result = await sinksStore.test(sink.id);
    if (result.ok) {
      toastsStore.push(`Test message delivered to "${sink.name}".`, "success");
    } else {
      toastsStore.push(`"${sink.name}" test failed: ${result.error}`, "danger");
    }
  } catch (error) {
    toastsStore.push(`"${sink.name}" test failed: ${error}`, "danger");
  } finally {
    testingId.value = null;
  }
}

async function remove(sink) {
  if (!window.confirm(`Delete sink "${sink.name}"?`)) return;
  try {
    await sinksStore.delete(sink.id);
    await sinksStore.getAll();
  } catch (error) {
    toastsStore.push(`Could not delete "${sink.name}": ${error}`, "danger");
  }
}
</script>

<template>
  <div class="card">
    <div
      class="card-header border-bottom d-flex justify-content-between align-items-center"
    >
      <h4 class="mb-0">Sinks</h4>
      <button
        v-if="canCreate"
        class="btn btn-primary btn-sm"
        @click="router.push('/sinks/add')"
      >
        New Sink
      </button>
    </div>
    <div class="card-body">
      <p class="text-muted">
        Destinations published indicators are pushed to: SIEMs over Splunk HEC,
        GELF or syslog/CEF, or any HTTP endpoint as a webhook.
      </p>
      <Spinner v-if="status.loading && !sinks.length" />
      <div v-else-if="status.error" class="text-danger">
        Error loading sinks: {{ status.error }}
      </div>
      <div v-else-if="!sinks.length" class="text-muted">No sinks yet.</div>
      <div v-else class="table-responsive">
        <table class="table align-middle">
          <thead>
            <tr>
              <th>name</th>
              <th v-if="!$isMobile">destination</th>
              <th v-if="!$isMobile">sends</th>
              <th>delivery</th>
              <th class="text-end">actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="sink in sinks" :key="sink.id">
              <td>
                <div class="form-check form-switch d-inline-block me-1">
                  <input
                    class="form-check-input"
                    type="checkbox"
                    :checked="sink.enabled"
                    :disabled="!canUpdate || togglingId === sink.id"
                    :title="sink.enabled ? 'Enabled' : 'Disabled'"
                    :aria-label="`${sink.enabled ? 'Disable' : 'Enable'} ${sink.name}`"
                    @change="toggleEnabled(sink)"
                  />
                </div>
                <span :class="{ 'text-muted': !sink.enabled }">{{
                  sink.name
                }}</span>
                <span class="badge bg-light text-dark ms-1">{{
                  TYPE_LABELS[sink.type] || sink.type
                }}</span>
              </td>
              <td
                v-if="!$isMobile"
                class="small font-monospace text-truncate"
                style="max-width: 260px"
                :title="destination(sink)"
              >
                {{ destination(sink) }}
              </td>
              <td v-if="!$isMobile" class="small text-muted">
                {{ filtersSummary(sink.filters) }}
              </td>
              <td class="small">
                <div v-if="failing(sink)" class="text-danger">
                  failing since {{ since(sink.last_error_at) }}
                  <div
                    class="text-truncate"
                    style="max-width: 280px"
                    :title="sink.last_error"
                  >
                    {{ sink.last_error }}
                  </div>
                </div>
                <div v-else-if="sink.last_success_at" class="text-success">
                  ok, {{ since(sink.last_success_at) }}
                </div>
                <div v-else class="text-muted">nothing delivered yet</div>
                <div class="text-muted">
                  {{ sink.delivered_count }} sent<template
                    v-if="sink.failed_count"
                    >, {{ sink.failed_count }} failed deliveries</template
                  >
                </div>
              </td>
              <td class="text-end text-nowrap">
                <button
                  v-if="canTest"
                  class="btn btn-outline-success btn-sm me-1"
                  title="Send one test indicator (192.0.2.1) now"
                  :disabled="testingId === sink.id"
                  @click="sendTest(sink)"
                >
                  {{ testingId === sink.id ? "…" : "Test" }}
                </button>
                <button
                  v-if="canUpdate"
                  class="btn btn-outline-primary btn-sm me-1"
                  @click="router.push(`/sinks/update/${sink.id}`)"
                >
                  Edit
                </button>
                <button
                  v-if="canDelete"
                  class="btn btn-outline-danger btn-sm"
                  @click="remove(sink)"
                >
                  Delete
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
