<script setup>
defineProps({
  modelValue: {
    type: String,
    required: true,
  },
});

const emit = defineEmits(["update:modelValue"]);

const feedTypes = [
  {
    value: "misp",
    label: "MISP Format",
    description: "Native MISP feeds with known structure and metadata.",
    icon: "bi bi-diagram-3",
  },
  {
    value: "csv",
    label: "CSV",
    description: "Tabular data requiring column-to-attribute mapping.",
    icon: "bi bi-table",
  },
  {
    value: "json",
    label: "JSON",
    description: "Structured JSON feeds with custom field mapping.",
    icon: "bi bi-braces",
  },
];

function select(value) {
  emit("update:modelValue", value);
}
</script>

<style scoped>
.feed-type-card {
  cursor: pointer;
  border: 1px solid var(--bs-border-color);
  transition: all 0.15s ease-in-out;
}

.feed-type-card:hover {
  border-color: var(--bs-primary);
  box-shadow: 0 0 0 1px rgba(13, 110, 253, 0.25);
}

.feed-type-card.active {
  border-color: var(--bs-primary);
  background-color: rgba(13, 110, 253, 0.05);
}

.feed-type-card i {
  color: var(--bs-primary);
}
</style>

<template>
  <div class="feed-type-selector">
    <div class="row g-3">
      <div v-for="type in feedTypes" :key="type.value" class="col-md-4">
        <label
          class="feed-type-card card h-100"
          :class="{ active: modelValue === type.value }"
        >
          <input
            class="form-check-input d-none"
            type="radio"
            name="feedType"
            :value="type.value"
            :checked="modelValue === type.value"
            @change="select(type.value)"
          />

          <div class="card-body">
            <div class="d-flex align-items-center mb-2">
              <i :class="type.icon" class="me-2 fs-4"></i>
              <h5 class="mb-0">{{ type.label }}</h5>
            </div>

            <p class="text-muted mb-0">
              {{ type.description }}
            </p>
          </div>
        </label>
      </div>
    </div>
  </div>
</template>
