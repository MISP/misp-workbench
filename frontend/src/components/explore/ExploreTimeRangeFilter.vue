<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from "vue";
import flatpickr from "flatpickr";
import "flatpickr/dist/flatpickr.min.css";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faClock,
  faChevronDown,
  faChevronUp,
  faXmark,
} from "@fortawesome/free-solid-svg-icons";

const emit = defineEmits(["change"]);

const isOpen = ref(false);
const activeTab = ref("relative");
const panelRef = ref(null);

// relative tab
const relativeValue = ref(1);
const relativeUnit = ref("h");

// absolute tab
const absoluteFrom = ref("");
const absoluteTo = ref("");
const fromInputRef = ref(null);
const toInputRef = ref(null);
let fromPicker = null;
let toPicker = null;

const quickOptions = [
  { label: "Last 15 minutes", from: "now-15m", to: "now" },
  { label: "Last 30 minutes", from: "now-30m", to: "now" },
  { label: "Last 1 hour", from: "now-1h", to: "now" },
  { label: "Last 4 hours", from: "now-4h", to: "now" },
  { label: "Last 12 hours", from: "now-12h", to: "now" },
  { label: "Last 24 hours", from: "now-24h", to: "now" },
  { label: "Last 7 days", from: "now-7d", to: "now" },
  { label: "Last 30 days", from: "now-30d", to: "now" },
  { label: "Last 90 days", from: "now-90d", to: "now" },
  { label: "Last 1 year", from: "now-1y", to: "now" },
];

const unitOptions = [
  { label: "minutes", value: "m" },
  { label: "hours", value: "h" },
  { label: "days", value: "d" },
  { label: "weeks", value: "w" },
  { label: "months", value: "M" },
  { label: "years", value: "y" },
];

const DEFAULT_RANGE = { label: "Last 30 days", from: "now-30d", to: "now" };

const currentRange = ref({ mode: "relative", ...DEFAULT_RANGE });

const displayLabel = computed(() => {
  if (!currentRange.value) return "Time range";
  const { mode, label, from, to } = currentRange.value;
  if (label) return label;
  if (mode === "absolute") {
    const f = from ? new Date(from).toLocaleString() : "?";
    const t = to ? new Date(to).toLocaleString() : "?";
    return `${f} → ${t}`;
  }
  return "Time range";
});

function apply(range) {
  currentRange.value = range;
  emit("change", range);
  isOpen.value = false;
}

function applyQuick(opt) {
  apply({ mode: "relative", label: opt.label, from: opt.from, to: opt.to });
}

function applyRelativeCustom() {
  const unitLabel =
    unitOptions.find((u) => u.value === relativeUnit.value)?.label ??
    relativeUnit.value;
  apply({
    mode: "relative",
    label: `Last ${relativeValue.value} ${unitLabel}`,
    from: `now-${relativeValue.value}${relativeUnit.value}`,
    to: "now",
  });
}

function applyAbsolute() {
  if (!absoluteFrom.value || !absoluteTo.value) return;
  apply({ mode: "absolute", from: absoluteFrom.value, to: absoluteTo.value });
}

function _initPickers() {
  if (fromInputRef.value && !fromPicker) {
    fromPicker = flatpickr(fromInputRef.value, {
      enableTime: true,
      dateFormat: "Y-m-dTH:i:S",
      altInput: true,
      altFormat: "Y-m-d H:i",
      allowInput: true,
      disableMobile: true,
      onChange: (_, dateStr) => {
        absoluteFrom.value = dateStr;
      },
    });
  }
  if (toInputRef.value && !toPicker) {
    toPicker = flatpickr(toInputRef.value, {
      enableTime: true,
      dateFormat: "Y-m-dTH:i:S",
      altInput: true,
      altFormat: "Y-m-d H:i",
      allowInput: true,
      disableMobile: true,
      onChange: (_, dateStr) => {
        absoluteTo.value = dateStr;
      },
    });
  }
}

watch(
  () => [isOpen.value, activeTab.value],
  ([open, tab], [wasOpen]) => {
    if (!open && wasOpen) {
      fromPicker?.destroy();
      fromPicker = null;
      toPicker?.destroy();
      toPicker = null;
    }
    if (open && tab === "absolute") {
      setTimeout(_initPickers, 0);
    }
  },
);

function clear(e) {
  e.stopPropagation();
  currentRange.value = null;
  emit("change", null);
}

function _handleDocumentClick(e) {
  const el = panelRef.value;
  if (!el) return;
  if (isOpen.value && !el.contains(e.target)) isOpen.value = false;
}

onMounted(() => {
  document.addEventListener("click", _handleDocumentClick);
  emit("change", currentRange.value);
});
onUnmounted(() => {
  document.removeEventListener("click", _handleDocumentClick);
  fromPicker?.destroy();
  toPicker?.destroy();
});
</script>

<style scoped>
.time-range-filter {
  position: relative;
  width: fit-content;
}

.time-range-panel {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  z-index: 100;
  width: 360px;
  background: var(--bs-body-bg, #fff);
  border: 1px solid var(--bs-border-color, #dee2e6);
  border-radius: var(--bs-border-radius);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

@media (max-width: 767px) {
  .time-range-filter {
    width: 100%;
  }

  .time-range-filter > button {
    width: 100%;
    justify-content: center;
  }

  .time-range-panel {
    width: 100%;
    left: 0;
    right: 0;
  }
}

.quick-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
}
</style>

<template>
  <div class="time-range-filter" ref="panelRef">
    <button
      class="btn btn-outline-secondary d-flex align-items-center gap-2"
      type="button"
      @click="isOpen = !isOpen"
    >
      <FontAwesomeIcon :icon="faClock" />
      <span class="text-console">{{ displayLabel }}</span>
      <FontAwesomeIcon
        v-if="currentRange"
        :icon="faXmark"
        class="ms-1 text-muted"
        @click="clear"
      />
      <FontAwesomeIcon
        v-else
        :icon="isOpen ? faChevronUp : faChevronDown"
        class="text-muted"
      />
    </button>

    <div v-if="isOpen" class="time-range-panel">
      <ul class="nav nav-tabs px-2 pt-2">
        <li class="nav-item">
          <button
            class="nav-link"
            :class="{ active: activeTab === 'absolute' }"
            @click="activeTab = 'absolute'"
          >
            Absolute
          </button>
        </li>
        <li class="nav-item">
          <button
            class="nav-link"
            :class="{ active: activeTab === 'relative' }"
            @click="activeTab = 'relative'"
          >
            Relative
          </button>
        </li>
      </ul>

      <div class="p-3">
        <!-- Absolute -->
        <div v-if="activeTab === 'absolute'">
          <div class="mb-2">
            <label class="form-label small text-muted mb-1">From</label>
            <input
              ref="fromInputRef"
              class="form-control form-control-sm"
              placeholder="Select date"
            />
          </div>
          <div class="mb-3">
            <label class="form-label small text-muted mb-1">To</label>
            <input
              ref="toInputRef"
              class="form-control form-control-sm"
              placeholder="Select date"
            />
          </div>
          <button
            class="btn btn-primary btn-sm w-100"
            :disabled="!absoluteFrom || !absoluteTo"
            @click="applyAbsolute"
          >
            Apply
          </button>
        </div>

        <!-- Relative -->
        <div v-if="activeTab === 'relative'">
          <div class="quick-grid mb-3">
            <button
              v-for="opt in quickOptions"
              :key="opt.label"
              class="btn btn-sm text-start"
              :class="
                currentRange?.label === opt.label
                  ? 'btn-primary'
                  : 'btn-outline-secondary'
              "
              @click="applyQuick(opt)"
            >
              {{ opt.label }}
            </button>
          </div>
          <hr class="my-2" />
          <label class="form-label small text-muted mb-1">Custom</label>
          <div class="d-flex gap-2">
            <input
              type="number"
              class="form-control form-control-sm"
              v-model.number="relativeValue"
              min="1"
              style="width: 70px"
            />
            <select class="form-select form-select-sm" v-model="relativeUnit">
              <option v-for="u in unitOptions" :key="u.value" :value="u.value">
                {{ u.label }}
              </option>
            </select>
            <button class="btn btn-primary btn-sm" @click="applyRelativeCustom">
              Apply
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
