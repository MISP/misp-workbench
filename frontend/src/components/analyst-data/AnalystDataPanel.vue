<script setup>
import { ref, computed } from "vue";
import { storeToRefs } from "pinia";
import { useAnalystDataStore } from "@/stores";
import AnalystDataIndex from "@/components/analyst-data/AnalystDataIndex.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faCommentDots,
  faChevronDown,
  faChevronRight,
} from "@fortawesome/free-solid-svg-icons";

/**
 * Collapsible analyst data for one object. The index inside is only mounted
 * once opened, so a page full of objects does not fire a request each.
 */
const props = defineProps({
  object_uuid: { type: String, required: true },
  object_type: { type: String, required: true },
});

const analystDataStore = useAnalystDataStore();
const { threads } = storeToRefs(analystDataStore);

const open = ref(false);

// Only known once opened -- there is no count endpoint, and fetching one per
// object just to render a badge would defeat the point of loading lazily.
const count = computed(() => {
  void threads.value;
  return analystDataStore.countFor(props.object_uuid);
});
</script>

<template>
  <button
    type="button"
    class="btn btn-sm btn-link text-decoration-none px-0"
    @click="open = !open"
  >
    <FontAwesomeIcon
      :icon="open ? faChevronDown : faChevronRight"
      fixed-width
    />
    <FontAwesomeIcon :icon="faCommentDots" class="ms-1 me-1" />
    Analyst data
    <span v-if="open && count > 0" class="badge text-bg-secondary ms-1">
      {{ count }}
    </span>
  </button>

  <div v-if="open" class="mt-2">
    <AnalystDataIndex :object_uuid="object_uuid" :object_type="object_type" />
  </div>
</template>
