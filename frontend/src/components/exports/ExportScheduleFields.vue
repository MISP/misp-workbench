<script setup>
import { ref, reactive, watch, computed, onMounted } from "vue";

// Two-way bound value: { schedule: ScheduleTaskSchedule|null, schedule_enabled }
const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({ schedule: null, schedule_enabled: false }),
  },
});
const emit = defineEmits(["update:modelValue"]);

const enabled = ref(false);
const frequency = ref("daily"); // hourly | daily | weekly | monthly | custom
const timeOfDay = ref("02:00"); // HH:MM for daily/weekly/monthly
const minute = ref("0"); // for hourly
const dayOfWeek = ref("1"); // Monday, for weekly
const dayOfMonth = ref("1"); // for monthly
const cron = reactive({
  minute: "0",
  hour: "*",
  day_of_month: "*",
  month_of_year: "*",
  day_of_week: "*",
});

const DAYS = [
  { value: "0", label: "Sunday" },
  { value: "1", label: "Monday" },
  { value: "2", label: "Tuesday" },
  { value: "3", label: "Wednesday" },
  { value: "4", label: "Thursday" },
  { value: "5", label: "Friday" },
  { value: "6", label: "Saturday" },
];

function splitTime() {
  const [h, m] = (timeOfDay.value || "00:00").split(":");
  return {
    hour: String(parseInt(h, 10) || 0),
    minute: String(parseInt(m, 10) || 0),
  };
}

// Build a ScheduleTaskSchedule (crontab) from the current UI selections.
const builtSchedule = computed(() => {
  if (!enabled.value) return null;
  const base = {
    type: "crontab",
    minute: "*",
    hour: "*",
    day_of_week: "*",
    day_of_month: "*",
    month_of_year: "*",
  };
  if (frequency.value === "hourly") {
    return { ...base, minute: String(minute.value || "0") };
  }
  if (frequency.value === "daily") {
    const { hour, minute: m } = splitTime();
    return { ...base, minute: m, hour };
  }
  if (frequency.value === "weekly") {
    const { hour, minute: m } = splitTime();
    return { ...base, minute: m, hour, day_of_week: String(dayOfWeek.value) };
  }
  if (frequency.value === "monthly") {
    const { hour, minute: m } = splitTime();
    return { ...base, minute: m, hour, day_of_month: String(dayOfMonth.value) };
  }
  // custom
  return {
    type: "crontab",
    minute: cron.minute || "*",
    hour: cron.hour || "*",
    day_of_month: cron.day_of_month || "*",
    month_of_year: cron.month_of_year || "*",
    day_of_week: cron.day_of_week || "*",
  };
});

function emitValue() {
  emit("update:modelValue", {
    schedule: builtSchedule.value,
    schedule_enabled: enabled.value,
  });
}

watch(
  [
    enabled,
    frequency,
    timeOfDay,
    minute,
    dayOfWeek,
    dayOfMonth,
    () => ({ ...cron }),
  ],
  emitValue,
  { deep: true },
);

// Initialise UI from an incoming schedule (edit mode), inferring the preset.
function hydrate(value) {
  const s = value?.schedule;
  enabled.value = !!value?.schedule_enabled;
  if (!s) return;
  cron.minute = s.minute ?? "0";
  cron.hour = s.hour ?? "*";
  cron.day_of_month = s.day_of_month ?? "*";
  cron.month_of_year = s.month_of_year ?? "*";
  cron.day_of_week = s.day_of_week ?? "*";

  const pad = (v) => String(v).padStart(2, "0");
  const hm = `${pad(s.hour === "*" ? 0 : s.hour)}:${pad(s.minute === "*" ? 0 : s.minute)}`;

  if (
    s.day_of_week !== "*" &&
    s.day_of_month === "*" &&
    s.month_of_year === "*"
  ) {
    frequency.value = "weekly";
    dayOfWeek.value = String(s.day_of_week);
    timeOfDay.value = hm;
  } else if (
    s.day_of_month !== "*" &&
    s.month_of_year === "*" &&
    s.day_of_week === "*"
  ) {
    frequency.value = "monthly";
    dayOfMonth.value = String(s.day_of_month);
    timeOfDay.value = hm;
  } else if (
    s.hour !== "*" &&
    s.day_of_week === "*" &&
    s.day_of_month === "*"
  ) {
    frequency.value = "daily";
    timeOfDay.value = hm;
  } else if (s.hour === "*" && s.minute !== "*" && s.day_of_month === "*") {
    frequency.value = "hourly";
    minute.value = String(s.minute);
  } else {
    frequency.value = "custom";
  }
}

onMounted(() => hydrate(props.modelValue));
</script>

<template>
  <div>
    <div class="form-check form-switch mb-2">
      <input
        class="form-check-input"
        type="checkbox"
        role="switch"
        id="export-schedule-enabled"
        v-model="enabled"
      />
      <label class="form-check-label" for="export-schedule-enabled">
        Run on a schedule
      </label>
    </div>

    <template v-if="enabled">
      <div class="row g-2 align-items-end">
        <div class="col-sm-6">
          <label class="form-label small">Frequency</label>
          <select class="form-select" v-model="frequency">
            <option value="hourly">Hourly</option>
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
            <option value="custom">Custom (cron)</option>
          </select>
        </div>

        <div v-if="frequency === 'hourly'" class="col-sm-6">
          <label class="form-label small">At minute</label>
          <input
            type="number"
            min="0"
            max="59"
            class="form-control"
            v-model="minute"
          />
        </div>

        <div
          v-if="['daily', 'weekly', 'monthly'].includes(frequency)"
          class="col-sm-6"
        >
          <label class="form-label small">At time</label>
          <input type="time" class="form-control" v-model="timeOfDay" />
        </div>

        <div v-if="frequency === 'weekly'" class="col-sm-6">
          <label class="form-label small">Day of week</label>
          <select class="form-select" v-model="dayOfWeek">
            <option v-for="d in DAYS" :key="d.value" :value="d.value">
              {{ d.label }}
            </option>
          </select>
        </div>

        <div v-if="frequency === 'monthly'" class="col-sm-6">
          <label class="form-label small">Day of month</label>
          <input
            type="number"
            min="1"
            max="31"
            class="form-control"
            v-model="dayOfMonth"
          />
        </div>
      </div>

      <div v-if="frequency === 'custom'" class="row g-2 mt-1">
        <div class="col">
          <label class="form-label small">minute</label>
          <input class="form-control font-monospace" v-model="cron.minute" />
        </div>
        <div class="col">
          <label class="form-label small">hour</label>
          <input class="form-control font-monospace" v-model="cron.hour" />
        </div>
        <div class="col">
          <label class="form-label small">day (month)</label>
          <input
            class="form-control font-monospace"
            v-model="cron.day_of_month"
          />
        </div>
        <div class="col">
          <label class="form-label small">month</label>
          <input
            class="form-control font-monospace"
            v-model="cron.month_of_year"
          />
        </div>
        <div class="col">
          <label class="form-label small">day (week)</label>
          <input
            class="form-control font-monospace"
            v-model="cron.day_of_week"
          />
        </div>
      </div>

      <div class="form-text">
        Each run overwrites the previous export file. Times are in the server
        timezone (UTC).
      </div>
    </template>
  </div>
</template>
