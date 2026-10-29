<script setup>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faChevronDown, faChevronUp } from "@fortawesome/free-solid-svg-icons";

// The keyboard's way to open a result card (a click anywhere also does).
defineProps({ expanded: { type: Boolean, required: true } });
defineEmits(["toggle"]);
</script>

<template>
  <button
    type="button"
    class="btn btn-sm btn-link text-muted p-0"
    :aria-expanded="expanded"
    :title="expanded ? 'Hide details' : 'Show details'"
    @click="$emit('toggle')"
  >
    <FontAwesomeIcon :icon="expanded ? faChevronUp : faChevronDown" />
  </button>
</template>
