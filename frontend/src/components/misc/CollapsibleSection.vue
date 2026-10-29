<script setup>
import { ref } from "vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faChevronDown, faChevronUp } from "@fortawesome/free-solid-svg-icons";

// A card whose body opens on demand; the header keeps a one-line summary of
// what is inside (the rules applied, non-default settings) while it is closed.
const props = defineProps({
  title: { type: String, required: true },
  summary: { type: String, default: "" },
  open: { type: Boolean, default: false },
});

const isOpen = ref(props.open);
</script>

<template>
  <div class="card">
    <button
      type="button"
      class="card-header btn text-start d-flex align-items-center gap-2 border-0 rounded-top"
      :aria-expanded="isOpen"
      @click="isOpen = !isOpen"
    >
      <h5 class="mb-0">{{ title }}</h5>
      <span v-if="summary" class="small text-muted text-truncate">
        {{ summary }}
      </span>
      <FontAwesomeIcon
        :icon="isOpen ? faChevronUp : faChevronDown"
        class="ms-auto text-muted"
      />
    </button>
    <div v-show="isOpen" class="card-body">
      <slot />
    </div>
  </div>
</template>
