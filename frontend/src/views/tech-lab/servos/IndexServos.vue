<script setup>
import { computed, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { useServosStore, useAuthStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import ServoActions from "@/components/servos/ServoActions.vue";
import PipelineViewer from "@/components/servos/PipelineViewer.vue";
import { authHelper } from "@/helpers";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faLock, faGears } from "@fortawesome/free-solid-svg-icons";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const route = useRoute();
const router = useRouter();
const servosStore = useServosStore();
const authStore = useAuthStore();
const { servos, pipelines, status } = storeToRefs(servosStore);
const { scopes } = storeToRefs(authStore);

const canCreate = computed(() =>
  authHelper.hasScope(scopes.value, "servos:create"),
);

const TABS = [
  { id: "servos", label: "Custom servos", icon: faGears },
  { id: "system", label: "System pipelines", icon: faLock },
];

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
  return pipelines.value ? systemPipelines.value.length : null;
}

function refresh() {
  servosStore.getAll();
  servosStore.getPipelines();
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
    <div v-show="activeTab === 'servos'">
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
              <th>name</th>
              <th>pipeline</th>
              <th>processors</th>
              <th>updated</th>
              <th>status</th>
              <th class="text-end">actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="servo in servos.items" :key="servo.id">
              <td>
                <RouterLink
                  :to="`/tech-lab/servos/${servo.id}`"
                  class="fw-semibold text-decoration-none"
                >
                  {{ servo.name }}
                </RouterLink>
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
    <div v-show="activeTab === 'system'">
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
  </div>
</template>
