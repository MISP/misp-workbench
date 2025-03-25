<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from "vue";
import flatpickr from "flatpickr";
import "flatpickr/dist/flatpickr.min.css";
import { useField } from "vee-validate";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faCalendar, faDeleteLeft } from "@fortawesome/free-solid-svg-icons";

const props = defineProps({
  name: {
    type: String,
    required: true,
  },
  dateFormat: {
    type: String,
    default: "Y-m-d",
  },
  altFormat: {
    type: String,
    default: "Y-m-d",
  },
  enableTime: {
    type: Boolean,
    default: false,
  },
  modelValue: {
    default: "",
  },
});

const emit = defineEmits(["update:modelValue"]);

const { value: fieldValue, errorMessage, setTouched } = useField(props.name);

const datepickerInput = ref(null);
let datepickerInstance = null;

onMounted(() => {
  datepickerInstance = flatpickr(datepickerInput.value, {
    dateFormat: props.dateFormat,
    altFormat: props.altFormat,
    enableTime: props.enableTime,
    altInput: true,
    allowInput: true,
    defaultDate:
      props.modelValue && props.dateFormat === "U"
        ? new Date(props.modelValue * 1000)
        : props.modelValue,
    onChange: (selectedDates, dateStr) => {
      fieldValue.value = dateStr;
      emit("update:modelValue", dateStr);
    },
  });
});

onUnmounted(() => {
  if (datepickerInstance) {
    datepickerInstance.destroy();
  }
});

watch(
  () => props.modelValue,
  (newValue) => {
    if (datepickerInstance) {
      datepickerInstance.setDate(newValue, false);
    }
  },
);

const error = computed(() => errorMessage.value);
</script>

<style scoped>
.is-invalid {
  border-color: red;
}

.error-message {
  color: red;
  font-size: 0.875rem;
}
</style>

<template>
  <div>
    <div class="input-group d-flex">
      <span class="input-group-text">
        <FontAwesomeIcon :icon="faCalendar" />
      </span>
      <input
        ref="datepickerInput"
        class="form-control"
        :class="{ 'is-invalid': error }"
        @blur="setTouched"
      />

      <span
        class="input-group-text"
        v-if="datepickerInstance && datepickerInstance.selectedDates.length"
      >
        <a href="#" @click="datepickerInstance.clear()" aria-label="Clear date">
          <FontAwesomeIcon :icon="faDeleteLeft" class="text-danger" />
        </a>
      </span>
      <span v-if="error" class="error-message">{{ error }}</span>
    </div>
  </div>
</template>
