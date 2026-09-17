<script setup>
import { computed, onMounted, ref } from "vue";
import { storeToRefs } from "pinia";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { useServosStore, useAuthStore, useToastsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import ServoActions from "@/components/servos/ServoActions.vue";
import PipelineViewer from "@/components/servos/PipelineViewer.vue";
import { authHelper } from "@/helpers";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faLock,
  faGears,
  faArrowUp,
  faArrowDown,
  faTriangleExclamation,
  faTrashCan,
  faClockRotateLeft,
  faUpRightFromSquare,
} from "@fortawesome/free-solid-svg-icons";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const route = useRoute();
const router = useRouter();
const servosStore = useServosStore();
const authStore = useAuthStore();
const toastsStore = useToastsStore();
const { servos, pipelines, errors, runs, backfillPreview, status } =
  storeToRefs(servosStore);
const { scopes } = storeToRefs(authStore);

const canCreate = computed(() =>
  authHelper.hasScope(scopes.value, "servos:create"),
);
const canUpdate = computed(() =>
  authHelper.hasScope(scopes.value, "servos:update"),
);

// Failures are keyed by pipeline name, which is what the on_failure handler
// writes; the table rows know their slug.
function servoErrors(servo) {
  return errors.value?.[`servo_${servo.slug}`] ?? null;
}

function errorTitle(servo) {
  const entry = servoErrors(servo);
  if (!entry) return "";
  return entry.messages.map((m) => `${m.count}\u00d7 ${m.message}`).join("\n");
}

const reordering = ref(false);

// Order matters as soon as one servo reads a field another produced, so this
// swaps a servo with its neighbour and sends the whole order in one call --
// PATCHing each would rebuild the chain twice and leave it half-sorted between.
async function move(index, delta) {
  const items = servos.value?.items ?? [];
  const target = index + delta;
  if (target < 0 || target >= items.length) return;
  const ids = items.map((s) => s.id);
  [ids[index], ids[target]] = [ids[target], ids[index]];
  reordering.value = true;
  try {
    await servosStore.reorder(ids);
    await servosStore.getAll();
  } finally {
    reordering.value = false;
  }
}

const TABS = [
  { id: "servos", label: "Custom servos", icon: faGears },
  { id: "system", label: "System pipelines", icon: faLock },
  { id: "backfill", label: "Backfill", icon: faClockRotateLeft },
];

const canRunBackfill = computed(() =>
  authHelper.hasScope(scopes.value, "servos:run"),
);

const backfillFilter = ref("");
const previewing = ref(false);

// Previewed rather than run blind: a backfill rewrites live documents, and the
// operator should see how many before confirming.
async function previewBackfill() {
  previewing.value = true;
  try {
    await servosStore.previewBackfill(backfillFilter.value);
  } catch (err) {
    toastsStore.push(err || "Could not evaluate that filter.", "danger");
    servosStore.backfillPreview = null;
  } finally {
    previewing.value = false;
  }
}

// The count answers "how many"; this answers "which" -- the same filter run
// through Explore, so the documents can be inspected before they are rewritten.
const exploreLink = computed(() => {
  if (!backfillPreview.value) return null;
  return {
    path: "/explore",
    query: { q: backfillPreview.value.filter_query || "*" },
  };
});

async function runBackfill() {
  const scope = backfillFilter.value
    ? `attributes matching "${backfillFilter.value}"`
    : "EVERY attribute in the index";
  const servoList = (backfillPreview.value?.enabled_servos ?? []).join(", ");
  if (
    !confirm(
      `Re-apply the ingest chain to ${scope}?\n\n` +
        `This rewrites ${backfillPreview.value?.matches ?? "?"} documents in place and runs ` +
        `every enabled servo (${servoList || "none"}) plus GeoIP enrichment. ` +
        `It cannot be undone.`,
    )
  )
    return;

  try {
    await servosStore.startBackfill(backfillFilter.value);
    toastsStore.push("Backfill started.", "success");
    await servosStore.getRuns();
  } catch (err) {
    toastsStore.push(err || "Could not start the backfill.", "danger");
  }
}

// Jumping in from a servo's error badge: re-run just the documents that servo
// failed on. The chain still runs whole -- only the selection is narrowed.
function backfillServoErrors(servo) {
  backfillFilter.value = `expanded.servo_errors:servo_${servo.slug}*`;
  selectTab("backfill");
  previewBackfill();
}

// Shipped with misp-workbench and managed in the repo.
const systemPipelines = computed(
  () => pipelines.value?.filter((p) => p.kind === "system") ?? [],
);
// A pipeline in the cluster that is neither shipped nor backed by a servo row
// — put there by someone else, or left behind by a deleted servo. Read-only
// here because misp-workbench does not own it. Rare enough that it rides along
// in the system panel rather than earning a tab that is usually empty.
const externalPipelines = computed(
  () => pipelines.value?.filter((p) => p.kind === "external") ?? [],
);

// The tab lives in the query string so a link to the shipped chain survives a
// refresh and the back button — the same reasoning as the event view's tabs,
// without a second route that would collide with /tech-lab/servos/:id.
const activeTab = computed(() =>
  TABS.some((tab) => tab.id === route.query.tab) ? route.query.tab : "servos",
);

function selectTab(id) {
  router.replace({
    path: "/tech-lab/servos",
    query: id === "servos" ? {} : { tab: id },
  });
}

function tabCount(id) {
  if (id === "servos")
    return servos.value?.total ?? servos.value?.items?.length;
  if (id === "backfill") return runs.value?.length || null;
  return pipelines.value ? systemPipelines.value.length : null;
}

function refresh() {
  servosStore.getAll();
  servosStore.getPipelines();
  servosStore.getErrors();
  servosStore.getRuns();
}

onMounted(refresh);
</script>

<template>
  <div class="d-flex justify-content-between align-items-center mb-3">
    <div>
      <h4 class="mb-0">Transformation Servos</h4>
      <small class="text-muted">
        Tech Lab — OpenSearch ingest pipelines that normalise and enrich
        attributes as they are indexed.
      </small>
    </div>
    <RouterLink
      v-if="canCreate"
      to="/tech-lab/servos/add"
      class="btn btn-primary btn-sm"
    >
      + New Servo
    </RouterLink>
  </div>

  <ul class="nav nav-tabs">
    <li v-for="tabItem in TABS" :key="tabItem.id" class="nav-item">
      <button
        type="button"
        class="nav-link"
        :class="{ active: activeTab === tabItem.id }"
        :aria-current="activeTab === tabItem.id ? 'page' : undefined"
        @click="selectTab(tabItem.id)"
      >
        <FontAwesomeIcon :icon="tabItem.icon" /> {{ tabItem.label }}
        <span
          v-if="tabCount(tabItem.id) != null"
          class="badge ms-1"
          :class="
            activeTab === tabItem.id ? 'text-bg-primary' : 'text-bg-secondary'
          "
        >
          {{ tabCount(tabItem.id) }}
        </span>
      </button>
    </li>
  </ul>

  <div class="tab-panels border border-top-0 rounded-bottom p-3">
    <!-- Custom servos -->
    <div v-show="activeTab === 'servos'" data-tab-panel="servos">
      <Spinner v-if="status.loading" />
      <div
        v-else-if="servos && servos.items && servos.items.length === 0"
        class="text-center text-muted py-5"
      >
        <FontAwesomeIcon :icon="faGears" class="fs-1 opacity-25 mb-3" />
        <h6 class="mb-2">No custom servos yet</h6>
        <p class="small mx-auto mb-4" style="max-width: 34rem">
          A servo is an OpenSearch ingest pipeline that runs on every attribute
          as it is indexed. Use one to parse, normalise or enrich values before
          they reach search and correlation — splitting a URL into its host and
          path, say, or lowercasing domains so the same indicator written two
          ways lines up.
        </p>
        <RouterLink
          v-if="canCreate"
          to="/tech-lab/servos/add"
          class="btn btn-outline-primary btn-sm"
        >
          + New Servo
        </RouterLink>
        <p v-else class="small fst-italic mb-0">
          Creating one needs the <code>servos:create</code> scope.
        </p>
      </div>
      <div v-else-if="servos && servos.items" class="table-responsive">
        <table class="table table-striped text-start align-middle mb-0">
          <thead>
            <tr>
              <th v-if="canUpdate" style="width: 5rem">order</th>
              <th>name</th>
              <th>pipeline</th>
              <th>processors</th>
              <th>updated</th>
              <th>status</th>
              <th class="text-end">actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(servo, index) in servos.items" :key="servo.id">
              <td v-if="canUpdate">
                <div class="btn-group btn-group-sm" role="group">
                  <button
                    class="btn btn-outline-secondary btn-sm py-0 px-1"
                    title="Run earlier"
                    :disabled="index === 0 || reordering"
                    @click="move(index, -1)"
                  >
                    <FontAwesomeIcon :icon="faArrowUp" />
                  </button>
                  <button
                    class="btn btn-outline-secondary btn-sm py-0 px-1"
                    title="Run later"
                    :disabled="index === servos.items.length - 1 || reordering"
                    @click="move(index, 1)"
                  >
                    <FontAwesomeIcon :icon="faArrowDown" />
                  </button>
                </div>
              </td>
              <td>
                <RouterLink
                  :to="`/tech-lab/servos/${servo.id}`"
                  class="fw-semibold text-decoration-none"
                >
                  {{ servo.name }}
                </RouterLink>
                <span
                  v-if="servo.drops_documents"
                  class="badge text-bg-warning ms-2"
                  title="This servo contains a drop processor: attributes it drops are never indexed, and creating one is rejected rather than silently succeeding."
                >
                  <FontAwesomeIcon :icon="faTrashCan" class="me-1" />discards
                </span>
                <div v-if="servo.description" class="text-muted small">
                  {{ servo.description }}
                </div>
              </td>
              <td class="font-monospace small">servo_{{ servo.slug }}</td>
              <td class="small">{{ servo.processors.length }}</td>
              <td class="text-muted small">
                {{
                  dayjs
                    .utc(servo.updated_at ?? servo.created_at)
                    .local()
                    .fromNow()
                }}
              </td>
              <td>
                <span
                  class="badge"
                  :class="servo.enabled ? 'bg-success' : 'bg-secondary'"
                  >{{ servo.enabled ? "enabled" : "disabled" }}</span
                >
                <button
                  v-if="servoErrors(servo)"
                  class="badge text-bg-danger ms-1 border-0"
                  :title="
                    canRunBackfill
                      ? `${errorTitle(servo)}\n\nClick to re-run the chain over just these documents.`
                      : errorTitle(servo)
                  "
                  :disabled="!canRunBackfill"
                  @click="backfillServoErrors(servo)"
                >
                  <FontAwesomeIcon :icon="faTriangleExclamation" class="me-1" />
                  {{ servoErrors(servo).count }}
                </button>
              </td>
              <td class="text-end">
                <ServoActions
                  :servo="servo"
                  @deleted="refresh()"
                  @updated="refresh()"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- System pipelines -->
    <div v-show="activeTab === 'system'" data-tab-panel="system">
      <p class="text-muted small">
        Shipped with misp-workbench and managed in the repository under
        <code>opensearch/pipelines/</code>. Read-only here — OpenSearch records
        no modification time for a pipeline, so these have no "updated" column.
      </p>
      <Spinner v-if="status.loadingPipelines" />
      <div v-else>
        <PipelineViewer
          v-for="pipeline in systemPipelines"
          :key="pipeline.name"
          :pipeline="pipeline"
        />

        <template v-if="externalPipelines.length">
          <h6 class="text-uppercase text-muted small mt-4">
            Other pipelines
            <span class="badge text-bg-secondary ms-1">{{
              externalPipelines.length
            }}</span>
          </h6>
          <p class="text-muted small">
            Present in the cluster but not managed by misp-workbench — put there
            by another tool, or left behind by a servo that was deleted from the
            database without its pipeline being removed.
          </p>
          <PipelineViewer
            v-for="pipeline in externalPipelines"
            :key="pipeline.name"
            :pipeline="pipeline"
          />
        </template>
      </div>
    </div>

    <!-- Backfill -->
    <div v-show="activeTab === 'backfill'" data-tab-panel="backfill">
      <div class="alert alert-warning d-flex gap-2 align-items-start py-2">
        <FontAwesomeIcon :icon="faTriangleExclamation" class="mt-1" />
        <div class="small">
          Servos only affect attributes indexed <strong>after</strong> they were
          enabled. A backfill re-applies them to what is already in the index by
          rewriting those documents in place — it cannot be undone.
          <br />
          It is <strong>chain-wide</strong>: OpenSearch re-runs the index's
          final pipeline on every document it touches, so GeoIP and
          <em>every enabled servo</em> run, not just one. Narrow
          <em>which documents</em> with a filter; you cannot narrow which
          servos.
        </div>
      </div>

      <div class="card mb-3">
        <div class="card-body">
          <label class="form-label small">
            filter
            <span class="text-muted">(Lucene, same syntax as Explore)</span>
          </label>
          <div class="input-group input-group-sm mb-2">
            <input
              v-model="backfillFilter"
              class="form-control font-monospace"
              placeholder="leave empty for every attribute — e.g. type:url"
              @keyup.enter="previewBackfill"
            />
            <button
              class="btn btn-outline-warning"
              :disabled="previewing"
              @click="previewBackfill"
            >
              {{ previewing ? "checking…" : "check" }}
            </button>
          </div>

          <div v-if="backfillPreview" class="small">
            <span
              class="badge me-2"
              :class="
                backfillPreview.matches
                  ? 'text-bg-primary'
                  : 'text-bg-secondary'
              "
              >{{ backfillPreview.matches }}</span
            >
            attribute{{ backfillPreview.matches === 1 ? "" : "s" }} would be
            rewritten, running
            <code
              v-for="slug in backfillPreview.enabled_servos"
              :key="slug"
              class="me-1"
              >servo_{{ slug }}</code
            ><span
              v-if="!backfillPreview.enabled_servos.length"
              class="text-muted"
              >no servos (GeoIP only)</span
            >.
            <RouterLink
              v-if="backfillPreview.matches"
              :to="exploreLink"
              target="_blank"
              class="ms-1 text-nowrap"
            >
              <FontAwesomeIcon :icon="faUpRightFromSquare" class="me-1" />
              see them in Explore
            </RouterLink>
          </div>
          <p v-else class="text-muted small fst-italic mb-0">
            Check a filter to see how many attributes it matches.
          </p>
        </div>
        <div class="card-footer text-end">
          <button
            v-if="canRunBackfill"
            class="btn btn-danger btn-sm"
            :disabled="!backfillPreview || status.backfilling"
            @click="runBackfill"
          >
            {{
              status.backfilling
                ? "starting…"
                : "Re-apply to matching attributes"
            }}
          </button>
          <span v-else class="text-muted small fst-italic">
            Running a backfill needs the <code>servos:run</code> scope.
          </span>
        </div>
      </div>

      <h6 class="text-uppercase text-muted small mt-4">Run history</h6>
      <p v-if="!runs.length" class="text-muted small">No backfills yet.</p>
      <div v-else class="table-responsive">
        <table class="table table-sm table-striped align-middle">
          <thead>
            <tr>
              <th>started</th>
              <th>filter</th>
              <th>status</th>
              <th class="text-end">rewritten</th>
              <th class="text-end">failures</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="run in runs" :key="run.id">
              <td class="text-muted small">
                {{ dayjs.utc(run.created_at).local().fromNow() }}
              </td>
              <td class="font-monospace small">
                {{ run.filter_query || "every attribute" }}
              </td>
              <td>
                <span
                  class="badge"
                  :class="{
                    'bg-success': run.status === 'success',
                    'bg-danger': run.status === 'failed',
                    'bg-secondary': run.status === 'queued',
                    'bg-info text-dark': run.status === 'running',
                  }"
                  :title="run.error || ''"
                  >{{ run.status }}</span
                >
              </td>
              <td class="text-end small">
                {{ run.updated }} / {{ run.total }}
              </td>
              <td class="text-end small">
                <span v-if="run.failure_count" class="text-danger">{{
                  run.failure_count
                }}</span>
                <span v-else class="text-muted">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
