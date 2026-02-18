<script setup>
import { ref, reactive, computed, watch } from "vue";
import { describeCron } from "@/helpers";

const props = defineProps({
  initialSchedule: {
    type: Object,
    default: () => ({ type: "interval", every: 1, unit: "days" }),
  },
});

const emit = defineEmits(["valid-change"]);

// Unique ID so multiple ScheduleEditor instances on the same page don't share radio button IDs.
const uid = Math.random().toString(36).substring(2, 8);

const unitMultipliers = { seconds: 1, minutes: 60, hours: 3600, days: 86400 };

const CRON_FIELDS = [
  { key: "minute", label: "minute", range: [0, 59] },
  { key: "hour", label: "hour", range: [0, 23] },
  { key: "dayOfMonth", label: "day of month", range: [1, 31] },
  { key: "month", label: "month", range: [1, 12] },
  { key: "dayOfWeek", label: "day of week", range: [0, 6] },
];

const CRON_PRESETS = [
  {
    label: "@hourly",
    minute: "0",
    hour: "*",
    dayOfMonth: "*",
    month: "*",
    dayOfWeek: "*",
  },
  {
    label: "@daily",
    minute: "0",
    hour: "0",
    dayOfMonth: "*",
    month: "*",
    dayOfWeek: "*",
  },
  {
    label: "@weekly",
    minute: "0",
    hour: "0",
    dayOfMonth: "*",
    month: "*",
    dayOfWeek: "0",
  },
  {
    label: "@monthly",
    minute: "0",
    hour: "0",
    dayOfMonth: "1",
    month: "*",
    dayOfWeek: "*",
  },
  {
    label: "@yearly",
    minute: "0",
    hour: "0",
    dayOfMonth: "1",
    month: "1",
    dayOfWeek: "*",
  },
];

const scheduleMode = ref("interval");
const every = ref(1);
const unit = ref("minutes");
const cron = reactive({
  minute: "*",
  hour: "*",
  dayOfMonth: "*",
  month: "*",
  dayOfWeek: "*",
});

function init(schedule) {
  if (!schedule) return;
  if (schedule.type === "crontab") {
    scheduleMode.value = "crontab";
    cron.minute = schedule.minute ?? "*";
    cron.hour = schedule.hour ?? "*";
    cron.dayOfMonth = schedule.dayOfMonth ?? "*";
    cron.month = schedule.month ?? "*";
    cron.dayOfWeek = schedule.dayOfWeek ?? "*";
  } else {
    scheduleMode.value = "interval";
    every.value = schedule.every ?? 1;
    unit.value = schedule.unit ?? "minutes";
  }
}

init(props.initialSchedule);
watch(() => props.initialSchedule, init, { deep: true });

function isValidCronPart(value, min, max) {
  const v = (value ?? "").trim();
  if (!v) return false;
  if (v === "*") return true;
  if (/^\*\/\d+$/.test(v)) return parseInt(v.split("/")[1]) > 0;
  if (/^\d+$/.test(v)) {
    const n = parseInt(v);
    return n >= min && n <= max;
  }
  if (/^\d+-\d+$/.test(v)) {
    const [a, b] = v.split("-").map(Number);
    return a >= min && b <= max && a <= b;
  }
  if (/^[\d,]+$/.test(v))
    return v.split(",").every((p) => {
      const n = parseInt(p);
      return n >= min && n <= max;
    });
  return false;
}

const cronFieldValidation = computed(() => ({
  minute: isValidCronPart(cron.minute, 0, 59),
  hour: isValidCronPart(cron.hour, 0, 23),
  dayOfMonth: isValidCronPart(cron.dayOfMonth, 1, 31),
  month: isValidCronPart(cron.month, 1, 12),
  dayOfWeek: isValidCronPart(cron.dayOfWeek, 0, 6),
}));

const isCronValid = computed(() =>
  Object.values(cronFieldValidation.value).every(Boolean),
);

const isValid = computed(() =>
  scheduleMode.value === "interval" ? every.value >= 1 : isCronValid.value,
);

watch(isValid, (val) => emit("valid-change", val), { immediate: true });

const cronExpression = computed(
  () =>
    `${cron.minute} ${cron.hour} ${cron.dayOfMonth} ${cron.month} ${cron.dayOfWeek}`,
);

const cronDescription = computed(() =>
  isCronValid.value
    ? describeCron(
        cron.minute,
        cron.hour,
        cron.dayOfMonth,
        cron.month,
        cron.dayOfWeek,
      )
    : "invalid expression",
);

function applyPreset(preset) {
  cron.minute = preset.minute;
  cron.hour = preset.hour;
  cron.dayOfMonth = preset.dayOfMonth;
  cron.month = preset.month;
  cron.dayOfWeek = preset.dayOfWeek;
}

function buildSchedule() {
  if (scheduleMode.value === "interval") {
    return {
      type: "interval",
      every: every.value * unitMultipliers[unit.value],
    };
  }
  return {
    type: "crontab",
    minute: cron.minute,
    hour: cron.hour,
    day_of_month: cron.dayOfMonth,
    month_of_year: cron.month,
    day_of_week: cron.dayOfWeek,
  };
}

function reset() {
  scheduleMode.value = "interval";
  every.value = 1;
  unit.value = "minutes";
  Object.assign(cron, {
    minute: "*",
    hour: "*",
    dayOfMonth: "*",
    month: "*",
    dayOfWeek: "*",
  });
}

defineExpose({ buildSchedule, reset });
</script>

<template>
  <div>
    <!-- Interval / Crontab toggle -->
    <div class="btn-group w-100 mb-3" role="group">
      <input
        type="radio"
        class="btn-check"
        :id="`modeInterval_${uid}`"
        value="interval"
        v-model="scheduleMode"
        autocomplete="off"
      />
      <label class="btn btn-outline-secondary" :for="`modeInterval_${uid}`"
        >Interval</label
      >
      <input
        type="radio"
        class="btn-check"
        :id="`modeCrontab_${uid}`"
        value="crontab"
        v-model="scheduleMode"
        autocomplete="off"
      />
      <label class="btn btn-outline-secondary" :for="`modeCrontab_${uid}`"
        >Crontab</label
      >
    </div>

    <!-- Interval -->
    <div v-if="scheduleMode === 'interval'" class="row g-2">
      <div class="col">
        <label :for="`every_${uid}`" class="form-label">Every</label>
        <input
          :id="`every_${uid}`"
          v-model.number="every"
          type="number"
          min="1"
          class="form-control"
        />
      </div>
      <div class="col">
        <label :for="`unit_${uid}`" class="form-label">Unit</label>
        <select :id="`unit_${uid}`" v-model="unit" class="form-select">
          <option value="seconds">Seconds</option>
          <option value="minutes">Minutes</option>
          <option value="hours">Hours</option>
          <option value="days">Days</option>
        </select>
      </div>
    </div>

    <!-- Crontab -->
    <div v-else>
      <!-- 5 fields -->
      <div class="d-flex gap-2 mb-1">
        <div
          v-for="field in CRON_FIELDS"
          :key="field.key"
          class="text-center flex-fill"
        >
          <input
            type="text"
            class="form-control form-control-sm text-center font-monospace"
            :class="{ 'is-invalid': !cronFieldValidation[field.key] }"
            v-model="cron[field.key]"
            :title="`${field.label} (${field.range[0]}–${field.range[1]})`"
          />
          <small class="text-muted">{{ field.label }}</small>
        </div>
      </div>

      <!-- Description -->
      <div
        class="rounded border px-3 py-2 my-2"
        :class="!isCronValid ? 'border-danger bg-danger bg-opacity-10' : ''"
      >
        <code class="text-secondary small">{{ cronExpression }}</code>
        <div
          class="fw-semibold mt-1"
          :class="isCronValid ? 'text-body' : 'text-danger'"
        >
          {{ cronDescription }}
        </div>
      </div>

      <!-- Presets -->
      <div class="d-flex gap-1 flex-wrap">
        <button
          v-for="preset in CRON_PRESETS"
          :key="preset.label"
          type="button"
          class="btn btn-sm btn-outline-secondary font-monospace"
          @click="applyPreset(preset)"
        >
          {{ preset.label }}
        </button>
      </div>

      <!-- Cheatsheet -->
      <table class="table table-sm mt-2 mb-0 text-muted small w-auto mx-auto">
        <tbody>
          <tr>
            <td class="font-monospace ps-0 pe-3 py-0">*</td>
            <td class="py-0">any value</td>
          </tr>
          <tr>
            <td class="font-monospace ps-0 pe-3 py-0">,</td>
            <td class="py-0">value list separator</td>
          </tr>
          <tr>
            <td class="font-monospace ps-0 pe-3 py-0">-</td>
            <td class="py-0">range of values</td>
          </tr>
          <tr>
            <td class="font-monospace ps-0 pe-3 py-0">/</td>
            <td class="py-0">step values</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
