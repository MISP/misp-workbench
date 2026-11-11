<script setup>
import { ref, computed, watch } from "vue";

// How often an organisation warninglist syncs from its URL, in minutes
// (v-model); 0 means manual syncs only ("Sync now").
const model = defineModel({ type: Number, default: 1440 });
const props = defineProps({
  id: { type: String, default: "sync-schedule" },
  size: { type: String, default: "" }, // "" | "sm"
});

// Bounds enforced by the API too.
const MIN = 15;
const MAX = 30 * 24 * 60;
const PRESETS = [
  { minutes: 60, label: "Every hour" },
  { minutes: 360, label: "Every 6 hours" },
  { minutes: 1440, label: "Daily" },
  { minutes: 10080, label: "Weekly" },
  { minutes: 0, label: "Manual only" },
];
const CUSTOM = "custom";

const isPreset = (m) => PRESETS.some((p) => p.minutes === m);
const choice = ref(isPreset(model.value) ? model.value : CUSTOM);
const custom = ref(isPreset(model.value) ? 120 : model.value);

watch(model, (m) => {
  if (isPreset(m)) choice.value = m;
  else {
    choice.value = CUSTOM;
    custom.value = m;
  }
});
watch([choice, custom], ([c, minutes]) => {
  model.value = c === CUSTOM ? Number(minutes) || 0 : c;
});

const customInvalid = computed(
  () =>
    choice.value === CUSTOM &&
    !(Number(custom.value) >= MIN && Number(custom.value) <= MAX),
);
defineExpose({ invalid: customInvalid });
</script>

<template>
  <div class="d-flex flex-wrap gap-2 align-items-start">
    <select
      :id="props.id"
      v-model="choice"
      class="form-select w-auto"
      :class="{ 'form-select-sm': props.size === 'sm' }"
    >
      <option v-for="p in PRESETS" :key="p.minutes" :value="p.minutes">
        {{ p.label }}
      </option>
      <option :value="CUSTOM">Custom…</option>
    </select>
    <div v-if="choice === CUSTOM" class="input-group w-auto">
      <span
        class="input-group-text"
        :class="{ 'py-0 small': props.size === 'sm' }"
        >every</span
      >
      <input
        v-model.number="custom"
        type="number"
        class="form-control"
        :class="{
          'is-invalid': customInvalid,
          'form-control-sm': props.size === 'sm',
        }"
        :min="MIN"
        :max="MAX"
        style="max-width: 7rem"
        :aria-label="'Sync every N minutes'"
      />
      <span
        class="input-group-text"
        :class="{ 'py-0 small': props.size === 'sm' }"
        >minutes</span
      >
    </div>
    <div v-if="customInvalid" class="text-danger small w-100">
      Between {{ MIN }} minutes and 30 days ({{ MAX }} minutes).
    </div>
  </div>
</template>
