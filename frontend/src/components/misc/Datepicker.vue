<template>
  <div>
    <input
      ref="datepickerInput"
      class="form-control"
      :class="{ 'is-invalid': error }"
      @blur="setTouched"
    />
    <span v-if="error" class="error-message">{{ error }}</span>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from "vue";
import flatpickr from "flatpickr";
import "flatpickr/dist/flatpickr.min.css";
import { useField } from "vee-validate";

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
    type: String,
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
  }
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
