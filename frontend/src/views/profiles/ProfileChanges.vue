<script setup>
import { ref, computed } from "vue";
import { storeToRefs } from "pinia";
import {
  useDetectionProfilesStore,
  useAuthStore,
  useToastsStore,
} from "@/stores";
import { authHelper } from "@/helpers";
import Spinner from "@/components/misc/Spinner.vue";
import Timestamp from "@/components/misc/Timestamp.vue";

// What a detection profile's next run changes against its last release,
// whether its approval gate holds it, and its recent runs.
const props = defineProps({ id: { type: [String, Number], required: true } });

const profilesStore = useDetectionProfilesStore();
const authStore = useAuthStore();
const toastsStore = useToastsStore();
const { scopes } = storeToRefs(authStore);

const canApprove = computed(() =>
  authHelper.hasScope(scopes.value, "indicators:review"),
);

const profile = ref(null);
const preview = ref(null);
const loading = ref(true);
const error = ref(null);
const approving = ref(false);

const RISKS = {
  popular_domain: "popular domain (top sites lists)",
  shared_infrastructure: "shared hosting, CDN or cloud",
  warninglisted: "on another warninglist",
  organisation_list: "on an organisation's list",
  new_source: "only from a new source",
  low_score: "low score",
};
const STATUS_CLASSES = {
  baseline: "text-bg-secondary",
  released: "text-bg-success",
  approved: "text-bg-primary",
  held: "text-bg-warning",
  lifted: "text-bg-light border",
};

async function load() {
  loading.value = true;
  error.value = null;
  try {
    [profile.value, preview.value] = await Promise.all([
      profilesStore.get(props.id),
      profilesStore.changes(props.id),
    ]);
  } catch (e) {
    error.value = e;
  } finally {
    loading.value = false;
  }
}

async function approve() {
  const { added, removed } = preview.value.changes;
  if (
    !confirm(
      `Release ${heldText(added, removed) || "the changes"} of "${profile.value.name}", held ones included? Its outputs run now.`,
    )
  )
    return;
  approving.value = true;
  try {
    await profilesStore.approveChanges(props.id, preview.value.fingerprint);
    toastsStore.push("Changes approved; its outputs run now.", "success");
    await load();
  } catch (e) {
    toastsStore.push(`${e}`, "danger");
    // Moved since previewed: show what they are now, to review again.
    await load();
  } finally {
    approving.value = false;
  }
}

// "3 additions", "1 addition and 2 removals": what is held, without zeros.
function heldText(added, removed) {
  const count = (n, noun) =>
    `${n.toLocaleString()} ${noun}${n === 1 ? "" : "s"}`;
  return [
    added ? count(added, "addition") : null,
    removed ? count(removed, "removal") : null,
  ]
    .filter(Boolean)
    .join(" and ");
}

const changes = computed(() => preview.value?.changes);
const hasChanges = computed(
  () => changes.value && (changes.value.added || changes.value.removed),
);
const riskRows = computed(() =>
  Object.entries(changes.value?.risks || {}).sort(
    (a, b) => b[1].count - a[1].count,
  ),
);
// Oldest first, for the trend.
const trend = computed(() =>
  [...(preview.value?.releases || [])].reverse().slice(-20),
);
const trendMax = computed(() =>
  Math.max(1, ...trend.value.map((r) => Math.max(r.added, r.removed))),
);
const barHeight = (n) => `${Math.max(n ? 3 : 0, (n / trendMax.value) * 60)}px`;

load();
</script>

<template>
  <div class="card">
    <div
      class="card-header border-bottom d-flex flex-wrap gap-2 justify-content-between align-items-center"
    >
      <h4 class="mb-0">
        Changes
        <span v-if="profile" class="text-muted fw-light"
          >· {{ profile.name }}</span
        >
      </h4>
      <div class="d-flex gap-2">
        <button
          type="button"
          class="btn btn-outline-secondary btn-sm"
          :disabled="loading"
          @click="load"
        >
          Refresh
        </button>
        <RouterLink
          :to="`/detection-profiles/update/${id}`"
          class="btn btn-outline-primary btn-sm"
          >Edit profile</RouterLink
        >
        <button
          v-if="canApprove"
          type="button"
          class="btn btn-success btn-sm"
          :disabled="approving || loading || (!hasChanges && !preview?.held)"
          title="Release the changes as they are now"
          @click="approve"
        >
          Approve changes
        </button>
      </div>
    </div>
    <div class="card-body">
      <Spinner v-if="loading && !preview" />
      <div v-else-if="error" class="alert alert-danger">{{ error }}</div>
      <template v-else-if="preview">
        <p class="text-muted">
          What the profile's next run changes in the controls it feeds (its
          exports, feeds and sinks keeping in step), against what it last
          released.
          <template v-if="preview.gate.enabled">
            Its approval gate keeps out of its outputs, until approved,
            <template v-if="preview.gate.hold_on_risk.length">
              additions flagged
              {{ preview.gate.hold_on_risk.map((f) => RISKS[f]).join(" or ") }};
            </template>
            <template v-if="preview.gate.max_additions !== null">
              a run's additions when there are more than
              {{ preview.gate.max_additions.toLocaleString() }};
            </template>
            <template v-if="preview.gate.spike_factor">
              a run's additions when they are
              {{ preview.gate.spike_factor }}× its usual;
            </template>
            <template v-if="preview.gate.max_removals !== null">
              a run's removals when there are more than
              {{ preview.gate.max_removals.toLocaleString() }};
            </template>
            everything else goes out.
          </template>
          <template v-else>
            It has no approval gate: every change goes out.
          </template>
        </p>

        <div v-if="preview.held" class="alert alert-warning">
          <strong>Held</strong> since
          <Timestamp :timestamp="preview.held_since" />:
          <template v-if="preview.held_added || preview.held_removed">
            {{ heldText(preview.held_added, preview.held_removed) }} kept out of
            its outputs until approved. The other changes go out.
          </template>
          <ul class="mb-0">
            <li v-for="r in preview.reasons" :key="r">{{ r }}</li>
          </ul>
          <div v-if="!preview.reasons.length" class="small">
            The changes pass the gate now; its next run or check lifts the hold.
          </div>
        </div>
        <div v-else-if="preview.reasons.length" class="alert alert-info">
          The next run will keep
          {{ heldText(preview.held_added, preview.held_removed) }} out of its
          outputs:
          <ul class="mb-0">
            <li v-for="r in preview.reasons" :key="r">{{ r }}</li>
          </ul>
        </div>
        <div v-else-if="changes.first" class="alert alert-secondary">
          Nothing released yet: the next run sets the baseline, without holding.
        </div>

        <div class="row g-3 mb-3 text-center">
          <div class="col-6 col-md-3">
            <div class="border rounded p-2">
              <div class="fs-4 font-monospace">
                {{ changes.members.toLocaleString() }}
              </div>
              <div class="small text-muted">selected now</div>
            </div>
          </div>
          <div class="col-6 col-md-3">
            <div class="border rounded p-2">
              <div class="fs-4 font-monospace">
                {{ changes.previous_members.toLocaleString() }}
              </div>
              <div class="small text-muted">last released</div>
            </div>
          </div>
          <div class="col-6 col-md-3">
            <div class="border rounded p-2">
              <div class="fs-4 font-monospace text-success">
                +{{ changes.added.toLocaleString() }}
              </div>
              <div class="small text-muted">
                to add
                <template v-if="changes.usual_added !== null">
                  (usually {{ Math.round(changes.usual_added) }})
                </template>
              </div>
            </div>
          </div>
          <div class="col-6 col-md-3">
            <div class="border rounded p-2">
              <div class="fs-4 font-monospace text-danger">
                −{{ changes.removed.toLocaleString() }}
              </div>
              <div class="small text-muted">to remove</div>
            </div>
          </div>
        </div>

        <h6 class="fw-semibold">Risk flags on additions</h6>
        <table class="table table-sm align-middle">
          <tbody>
            <tr v-for="[flag, risk] in riskRows" :key="flag">
              <td style="width: 1%" class="text-nowrap">
                <span
                  class="badge"
                  :class="
                    preview.gate.hold_on_risk.includes(flag)
                      ? 'text-bg-danger'
                      : 'text-bg-warning'
                  "
                  :title="
                    preview.gate.hold_on_risk.includes(flag)
                      ? 'The gate holds on this flag'
                      : 'Flagged; the gate doesn\'t hold on it'
                  "
                  >{{ RISKS[flag] || flag }}</span
                >
              </td>
              <td class="text-end font-monospace" style="width: 1%">
                {{ risk.count.toLocaleString() }}
              </td>
              <td class="small">
                <span
                  v-for="s in risk.sample"
                  :key="s.uuid"
                  class="me-3 d-inline-block text-break"
                  :title="s.detail"
                  ><span class="font-monospace">{{ s.value }}</span>
                  <span class="text-muted"> ({{ s.detail }})</span></span
                >
              </td>
            </tr>
            <tr v-if="!riskRows.length">
              <td class="text-muted">No addition is flagged.</td>
            </tr>
          </tbody>
        </table>

        <div class="row g-4">
          <div class="col-12 col-lg-6">
            <h6 class="fw-semibold text-success">Additions</h6>
            <div class="row small">
              <div class="col-6">
                <div class="text-muted">by type</div>
                <div
                  v-for="(n, type) in changes.added_by_type"
                  :key="type"
                  class="d-flex justify-content-between"
                >
                  <span>{{ type }}</span
                  ><span class="font-monospace">{{ n.toLocaleString() }}</span>
                </div>
              </div>
              <div class="col-6">
                <div class="text-muted">by source</div>
                <div
                  v-for="s in changes.added_by_source"
                  :key="s.key"
                  class="d-flex justify-content-between"
                >
                  <span class="text-truncate" :title="s.key">{{ s.name }}</span
                  ><span class="font-monospace">{{
                    s.count.toLocaleString()
                  }}</span>
                </div>
              </div>
            </div>
            <ul class="list-unstyled small mt-2 mb-0">
              <li
                v-for="s in changes.added_sample"
                :key="s.uuid"
                class="text-break"
              >
                <span class="text-muted">{{ s.type }}</span>
                <span class="font-monospace ms-1">{{ s.value }}</span>
                <span v-if="s.score !== null" class="text-muted ms-1"
                  >· {{ s.score }}</span
                >
              </li>
              <li
                v-if="changes.added > changes.added_sample.length"
                class="text-muted"
              >
                and
                {{
                  (changes.added - changes.added_sample.length).toLocaleString()
                }}
                more
              </li>
              <li v-if="!changes.added" class="text-muted">Nothing to add.</li>
            </ul>
          </div>
          <div class="col-12 col-lg-6">
            <h6 class="fw-semibold text-danger">Removals</h6>
            <div class="row small">
              <div class="col-6">
                <div class="text-muted">why</div>
                <div
                  v-for="(n, reason) in changes.removed_by_reason"
                  :key="reason"
                  class="d-flex justify-content-between"
                >
                  <span>{{ reason }}</span
                  ><span class="font-monospace">{{ n.toLocaleString() }}</span>
                </div>
              </div>
              <div class="col-6">
                <div class="text-muted">by type</div>
                <div
                  v-for="(n, type) in changes.removed_by_type"
                  :key="type"
                  class="d-flex justify-content-between"
                >
                  <span>{{ type }}</span
                  ><span class="font-monospace">{{ n.toLocaleString() }}</span>
                </div>
              </div>
            </div>
            <ul class="list-unstyled small mt-2 mb-0">
              <li
                v-for="s in changes.removed_sample"
                :key="s.uuid"
                class="text-break"
              >
                <span class="text-muted">{{ s.type || "purged" }}</span>
                <span class="font-monospace ms-1">{{ s.value || s.uuid }}</span>
                <span class="badge text-bg-light border ms-1">{{
                  s.detail
                }}</span>
              </li>
              <li
                v-if="changes.removed > changes.removed_sample.length"
                class="text-muted"
              >
                and
                {{
                  (
                    changes.removed - changes.removed_sample.length
                  ).toLocaleString()
                }}
                more
              </li>
              <li v-if="!changes.removed" class="text-muted">
                Nothing to remove.
              </li>
            </ul>
          </div>
        </div>

        <h6 class="fw-semibold mt-4">Recent runs</h6>
        <div
          v-if="trend.length"
          class="d-flex align-items-end gap-1 mb-2 trend"
          aria-label="Additions and removals of recent runs"
        >
          <div
            v-for="r in trend"
            :key="r.id"
            class="d-flex align-items-end gap-0"
            :title="`${r.status}: +${r.added} −${r.removed}`"
          >
            <div
              class="trend-bar bg-success"
              :class="{
                'opacity-50': r.status === 'held' || r.status === 'lifted',
              }"
              :style="{ height: barHeight(r.added) }"
            ></div>
            <div
              class="trend-bar bg-danger"
              :class="{
                'opacity-50': r.status === 'held' || r.status === 'lifted',
              }"
              :style="{ height: barHeight(r.removed) }"
            ></div>
          </div>
        </div>
        <div class="table-responsive">
          <table class="table table-sm align-middle small">
            <thead>
              <tr>
                <th>when</th>
                <th></th>
                <th class="text-end">added</th>
                <th class="text-end">removed</th>
                <th class="text-end">members</th>
                <th>by / why</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in preview.releases" :key="r.id">
                <td class="text-nowrap">
                  <Timestamp :timestamp="r.created_at" />
                </td>
                <td>
                  <span class="badge" :class="STATUS_CLASSES[r.status]">{{
                    r.status
                  }}</span>
                </td>
                <td class="text-end font-monospace text-success">
                  +{{ r.added.toLocaleString() }}
                </td>
                <td class="text-end font-monospace text-danger">
                  −{{ r.removed.toLocaleString() }}
                </td>
                <td class="text-end font-monospace">
                  {{ r.members.toLocaleString() }}
                </td>
                <td>
                  <span v-if="r.user_email">{{ r.user_email }}</span>
                  <span class="text-muted">{{ r.reasons.join("; ") }}</span>
                </td>
              </tr>
              <tr v-if="!preview.releases.length">
                <td colspan="6" class="text-muted">No run yet.</td>
              </tr>
            </tbody>
          </table>
        </div>

        <h6 class="fw-semibold mt-3">Outputs</h6>
        <ul class="list-unstyled small mb-0">
          <li v-for="c in preview.consumers" :key="`${c.kind}-${c.id}`">
            <RouterLink
              :to="
                c.kind === 'export'
                  ? '/exports'
                  : c.kind === 'edl'
                    ? `/edls/${c.id}`
                    : '/sinks'
              "
              >{{ c.name }}</RouterLink
            >
            <span class="text-muted ms-1">{{ c.kind }}</span>
            <span
              v-if="c.kind === 'export'"
              class="badge ms-1 text-bg-light border"
              >{{ c.status }}</span
            >
            <span v-else class="ms-1 text-muted">· {{ c.status }}</span>
            <span
              v-if="!c.gated"
              class="badge text-bg-light border ms-1"
              title="Sends values one at a time as events are published: not a run, nothing is held from it"
              >not gated</span
            >
          </li>
          <li v-if="!preview.consumers.length" class="text-muted">
            No export, sink or EDL uses this profile yet.
          </li>
        </ul>
      </template>
    </div>
  </div>
</template>

<style scoped>
.trend {
  height: 64px;
}
.trend-bar {
  width: 6px;
}
</style>
