<script setup>
import { computed } from "vue";
import {
  faCircle,
  faPause,
  faRotateRight,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

const props = defineProps({
  status: { type: String, default: "idle" }, // idle | busy | starting | dead
});

const emit = defineEmits(["interrupt", "restart"]);

const label = computed(() => {
  switch (props.status) {
    case "busy":
      return "Busy";
    case "starting":
      return "Starting";
    case "dead":
      return "Dead";
    default:
      return "Idle";
  }
});

const dotClass = computed(() => {
  switch (props.status) {
    case "busy":
      return "text-warning";
    case "starting":
      return "text-info";
    case "dead":
      return "text-danger";
    default:
      return "text-success";
  }
});
</script>

<template>
  <div class="kernel-pill d-inline-flex align-items-center gap-2">
    <span class="badge bg-body-secondary text-body border">
      <FontAwesomeIcon
        :icon="faCircle"
        :class="dotClass"
        class="me-1"
        style="font-size: 0.5rem"
      />
      kernel: {{ label }}
    </span>
    <button
      class="btn btn-link btn-sm p-0 text-secondary"
      :disabled="status !== 'busy'"
      @click="emit('interrupt')"
      title="Interrupt"
    >
      <FontAwesomeIcon :icon="faPause" />
    </button>
    <button
      class="btn btn-link btn-sm p-0 text-secondary"
      @click="emit('restart')"
      title="Restart kernel"
    >
      <FontAwesomeIcon :icon="faRotateRight" />
    </button>
  </div>
</template>
