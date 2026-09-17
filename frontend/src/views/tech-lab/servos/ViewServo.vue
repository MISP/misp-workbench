<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from "vue";
import { storeToRefs } from "pinia";
import { RouterLink } from "vue-router";
import { useServosStore, useAuthStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import ServoActions from "@/components/servos/ServoActions.vue";
import { authHelper } from "@/helpers";
import { VueMonacoEditor } from "@guolao/vue-monaco-editor";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faPen } from "@fortawesome/free-solid-svg-icons";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const props = defineProps({ id: { type: [String, Number], required: true } });

const servosStore = useServosStore();
const authStore = useAuthStore();
const { servo, status } = storeToRefs(servosStore);
const { scopes } = storeToRefs(authStore);

const canUpdate = computed(() =>
  authHelper.hasScope(scopes.value, "servos:update"),
);

const monacoOptions = {
  fontSize: 13,
  readOnly: true,
  minimap: { enabled: false },
  scrollBeyondLastLine: false,
  automaticLayout: true,
  tabSize: 2,
  wordWrap: "on",
  renderLineHighlight: "none",
};

function detectMonacoTheme() {
  return document.documentElement.getAttribute("data-bs-theme") === "dark"
    ? "vs-dark"
    : "vs";
}
const monacoTheme = ref(detectMonacoTheme());
let themeObserver = null;

const processorsJson = computed(() =>
  servo.value ? JSON.stringify(servo.value.processors, null, 2) : "",
);

onMounted(() => {
  servosStore.getById(props.id);
  themeObserver = new MutationObserver((mutations) => {
    if (mutations.some((m) => m.attributeName === "data-bs-theme")) {
      monacoTheme.value = detectMonacoTheme();
    }
  });
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-bs-theme"],
  });
});

onBeforeUnmount(() => {
  themeObserver?.disconnect();
  themeObserver = null;
});
</script>

<template>
  <Spinner v-if="status.loading || !servo" />
  <div v-else>
    <div class="d-flex justify-content-between align-items-start mb-3">
      <div>
        <h4 class="mb-0">
          {{ servo.name }}
          <span
            class="badge align-middle ms-2"
            :class="servo.enabled ? 'bg-success' : 'bg-secondary'"
            >{{ servo.enabled ? "enabled" : "disabled" }}</span
          >
        </h4>
        <small class="text-muted">
          <RouterLink to="/tech-lab/servos" class="text-decoration-none"
            >Transformation Servos</RouterLink
          >
          — pipeline <code>servo_{{ servo.slug }}</code> on
          <code>{{ servo.target_index }}</code>
        </small>
      </div>
      <div class="d-flex gap-2 align-items-center">
        <RouterLink
          v-if="canUpdate"
          :to="`/tech-lab/servos/update/${servo.id}`"
          class="btn btn-outline-primary btn-sm"
        >
          <FontAwesomeIcon :icon="faPen" class="me-1" />
          edit
        </RouterLink>
        <ServoActions
          :servo="servo"
          @deleted="$router.push('/tech-lab/servos')"
        />
      </div>
    </div>

    <p v-if="servo.description" class="text-muted">{{ servo.description }}</p>

    <dl class="row small">
      <dt class="col-sm-2">created</dt>
      <dd class="col-sm-4">
        {{ dayjs.utc(servo.created_at).local().format("YYYY-MM-DD HH:mm") }}
      </dd>
      <dt class="col-sm-2">updated</dt>
      <dd class="col-sm-4">
        {{
          servo.updated_at
            ? dayjs.utc(servo.updated_at).local().fromNow()
            : "never"
        }}
      </dd>
      <dt class="col-sm-2">last synced</dt>
      <dd class="col-sm-4">
        {{
          servo.last_synced_at
            ? dayjs.utc(servo.last_synced_at).local().fromNow()
            : "not applied"
        }}
      </dd>
      <dt class="col-sm-2">position</dt>
      <dd class="col-sm-4">{{ servo.position }}</dd>
    </dl>

    <div class="card">
      <div class="card-header">Processors</div>
      <div class="card-body p-0">
        <VueMonacoEditor
          :value="processorsJson"
          language="json"
          :theme="monacoTheme"
          :options="monacoOptions"
          height="480px"
        />
      </div>
    </div>
  </div>
</template>
