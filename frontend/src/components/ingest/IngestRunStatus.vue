<script setup>
import { computed, onMounted, onBeforeUnmount, watch, ref } from "vue";
import { storeToRefs } from "pinia";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { authHelper } from "@/helpers";
import { useAuthStore, useIngestRunsStore, useToastsStore } from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faStop } from "@fortawesome/free-solid-svg-icons";

dayjs.extend(relativeTime);

// A feed's fetches or a server's pulls (see docs/features/feeds): the run in
// progress, with its progress and a cancel button, and the last finished one.
const props = defineProps({
  kind: { type: String, required: true }, // "feed" | "server"
  sourceId: { type: Number, required: true },
  // A one-line badge for tables instead of the full card.
  compact: { type: Boolean, default: false },
});

const POLL_MS = 5_000;

const ingestRunsStore = useIngestRunsStore();
const toastsStore = useToastsStore();
const { runs } = storeToRefs(ingestRunsStore);
const { scopes } = storeToRefs(useAuthStore());

const cancelling = ref(false);
let timer = null;

const run = computed(() => runs.value[`${props.kind}:${props.sourceId}`]);
const current = computed(() => run.value?.current);
const last = computed(() => run.value?.last);

const canCancel = computed(() =>
  authHelper.hasScope(
    scopes.value,
    props.kind === "feed" ? "feeds:fetch" : "servers:pull",
  ),
);

const STATUS_CLASSES = {
  queued: "bg-secondary",
  running: "bg-primary",
  done: "bg-success",
  failed: "bg-danger",
  cancelled: "bg-secondary",
};
const STATUS_LABELS = {
  queued: "waiting for a slot",
  running: "ingesting",
  done: "done",
  failed: "failed",
  cancelled: "cancelled",
};

const percent = computed(() => {
  const r = current.value;
  if (!r || !r.total) return null;
  return Math.min(100, Math.round(((r.done + r.failed) / r.total) * 100));
});

function ago(seconds) {
  return seconds ? dayjs.unix(seconds).fromNow() : null;
}

function counts(r) {
  if (!r.total) return null;
  const failed = r.failed ? `, ${r.failed} failed` : "";
  return `${r.done} / ${r.total} events${failed}`;
}

const compactTitle = computed(() => {
  const r = current.value || last.value;
  if (!r) return "";
  return [
    STATUS_LABELS[r.status],
    counts(r),
    r.finished_at ? `finished ${ago(r.finished_at)}` : null,
    r.error,
  ]
    .filter(Boolean)
    .join(" · ");
});

async function load() {
  try {
    await ingestRunsStore.load(props.kind, props.sourceId);
  } catch {
    // The source may be gone, or the user may not read it; nothing to show.
  }
}

function tick() {
  if (
    current.value ||
    ingestRunsStore.isExpecting(props.kind, props.sourceId)
  ) {
    load();
  }
}

async function cancel() {
  cancelling.value = true;
  try {
    await ingestRunsStore.cancel(props.kind, props.sourceId);
    toastsStore.push(
      props.kind === "feed"
        ? "Feed fetch cancelled."
        : "Server pull cancelled.",
    );
  } catch (error) {
    toastsStore.push(`Could not cancel it: ${error}`, "error");
  } finally {
    cancelling.value = false;
  }
}

onMounted(() => {
  load();
  timer = setInterval(tick, POLL_MS);
});

onBeforeUnmount(() => clearInterval(timer));

watch(() => props.sourceId, load);
</script>

<template>
  <!-- Table cell: the run in progress, else the last one -->
  <span v-if="compact" :title="compactTitle">
    <template v-if="current">
      <span class="badge" :class="STATUS_CLASSES[current.status]">
        {{ STATUS_LABELS[current.status] }}
      </span>
      <span v-if="percent !== null" class="small text-muted ms-1"
        >{{ percent }}%</span
      >
    </template>
    <template v-else-if="last">
      <span class="badge" :class="STATUS_CLASSES[last.status]">
        {{ STATUS_LABELS[last.status] }}
      </span>
      <span class="small text-muted ms-1">{{ ago(last.finished_at) }}</span>
    </template>
    <span v-else class="small text-muted">never</span>
  </span>

  <div v-else class="card">
    <div class="card-header d-flex align-items-center">
      <h5 class="mb-0 me-auto">
        {{ kind === "feed" ? "Fetches" : "Pulls" }}
      </h5>
      <button
        v-if="current && canCancel"
        type="button"
        class="btn btn-outline-danger btn-sm"
        :disabled="cancelling"
        @click="cancel"
      >
        <FontAwesomeIcon :icon="faStop" class="me-1" />
        Cancel
      </button>
    </div>
    <div class="card-body">
      <div v-if="current" class="mb-3">
        <div class="d-flex align-items-center gap-2 mb-2">
          <span class="badge" :class="STATUS_CLASSES[current.status]">
            {{ STATUS_LABELS[current.status] }}
          </span>
          <span class="small text-muted">
            <template v-if="current.started_at"
              >started {{ ago(current.started_at) }}</template
            >
            <template v-else>queued {{ ago(current.queued_at) }}</template>
          </span>
        </div>
        <div v-if="percent !== null" class="progress mb-2" role="progressbar">
          <div
            class="progress-bar"
            :class="{
              'progress-bar-striped progress-bar-animated':
                current.status === 'running',
            }"
            :style="{ width: `${percent}%` }"
          ></div>
        </div>
        <div class="small text-muted">
          <template v-if="counts(current)">
            {{ counts(current) }} · {{ current.pending }} waiting
          </template>
          <template v-else-if="current.status === 'queued'">
            Other fetches and pulls are using every ingestion slot, or ingestion
            is paused (runtime settings, ingest).
          </template>
          <template v-else>Listing the events to ingest…</template>
        </div>
      </div>
      <p v-else class="text-muted small mb-3">
        No {{ kind === "feed" ? "fetch" : "pull" }} in progress.
      </p>

      <div v-if="last" class="border-top pt-3">
        <div class="d-flex align-items-center gap-2">
          <span class="small fw-semibold">Last</span>
          <span class="badge" :class="STATUS_CLASSES[last.status]">
            {{ STATUS_LABELS[last.status] }}
          </span>
          <span class="small text-muted">{{ ago(last.finished_at) }}</span>
          <span v-if="counts(last)" class="small text-muted">
            · {{ counts(last) }}
          </span>
        </div>
        <div
          v-if="last.error"
          class="small mt-1"
          :class="last.status === 'failed' ? 'text-danger' : 'text-muted'"
        >
          {{ last.error }}
        </div>
      </div>
    </div>
  </div>
</template>
