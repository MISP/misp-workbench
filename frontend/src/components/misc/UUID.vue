<script setup>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faCopy } from "@fortawesome/free-solid-svg-icons";

const props = defineProps(["uuid"]);

function copyUuidToClipboard() {
  navigator.clipboard.writeText(props.uuid);
}
</script>

<template>
  <span class="d-inline-flex align-items-center gap-1">
    <span class="badge bg-light text-dark shadow-sm mb-0">{{ uuid }}</span>
    <button type="button" class="btn btn-sm p-0 border-0 bg-transparent">
      <FontAwesomeIcon
        class="text-primary"
        :icon="faCopy"
        @click="copyUuidToClipboard"
      />
    </button>
  </span>
</template>
