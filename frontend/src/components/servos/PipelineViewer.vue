<script setup>
import { ref, watch } from "vue";
import { useServosStore } from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faLock,
  faChevronDown,
  faChevronRight,
} from "@fortawesome/free-solid-svg-icons";
import Spinner from "@/components/misc/Spinner.vue";

const props = defineProps({
  pipeline: { type: Object, required: true },
});

const servosStore = useServosStore();
const expanded = ref(false);
const definition = ref(null);
const loading = ref(false);

watch(expanded, async (open) => {
  if (!open || definition.value) return;
  loading.value = true;
  try {
    const detail = await servosStore.getPipeline(props.pipeline.name);
    definition.value = detail.definition;
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="border rounded mb-2">
    <button
      class="btn btn-link text-decoration-none w-100 text-start d-flex align-items-center gap-2 py-2 px-3"
      @click="expanded = !expanded"
    >
      <FontAwesomeIcon
        :icon="expanded ? faChevronDown : faChevronRight"
        class="text-muted small"
      />
      <span class="font-monospace">{{ pipeline.name }}</span>
      <FontAwesomeIcon
        v-if="pipeline.read_only"
        :icon="faLock"
        class="text-muted small"
        title="Read-only — managed in the misp-workbench repository"
      />
      <span class="badge bg-secondary ms-auto"
        >{{ pipeline.processor_count }} processor{{
          pipeline.processor_count === 1 ? "" : "s"
        }}</span
      >
    </button>
    <div v-if="expanded" class="px-3 pb-3">
      <p v-if="pipeline.description" class="text-muted small mb-2">
        {{ pipeline.description }}
      </p>
      <div class="mb-2">
        <span
          v-for="type in pipeline.processor_types"
          :key="type"
          class="badge bg-light text-dark border me-1 font-monospace fw-normal"
          >{{ type }}</span
        >
      </div>
      <Spinner v-if="loading" />
      <pre
        v-else-if="definition"
        class="bg-body-tertiary border rounded p-2 small mb-0 overflow-auto"
        style="max-height: 24rem"
        >{{ JSON.stringify(definition, null, 2) }}</pre
      >
    </div>
  </div>
</template>
