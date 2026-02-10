<script setup>
defineProps({
  modelValue: {
    type: String,
    required: true,
  },
});

const emit = defineEmits(["update:modelValue"]);

function select(value) {
  emit("update:modelValue", value);
}
</script>
<style scoped>
.mode-card {
  cursor: pointer;
  border: 1px solid var(--bs-border-color);
  transition: all 0.15s ease-in-out;
}

.mode-card:hover {
  border-color: var(--bs-primary);
  box-shadow: 0 0 0 1px rgba(13, 110, 253, 0.25);
}

.mode-card.active {
  border-color: var(--bs-primary);
  background-color: rgba(13, 110, 253, 0.05);
}
</style>

<template>
  <div class="mb-4">
    <div class="card">
      <div class="card-header">
        <h5 class="mb-0">CSV Parsing Mode</h5>
      </div>
      <div class="card-body">
        <div class="csv-mode-selector">
          <h6 class="mb-3">How should each row be interpreted?</h6>

          <div class="row g-3">
            <!-- Attribute mode -->
            <div class="col-md-6">
              <label
                class="mode-card card h-100"
                :class="{ active: modelValue === 'attribute' }"
              >
                <input
                  class="form-check-input d-none"
                  type="radio"
                  value="attribute"
                  :checked="modelValue === 'attribute'"
                  @change="select('attribute')"
                />

                <div class="card-body">
                  <h6 class="mb-2">Row → Attribute</h6>
                  <p class="text-muted mb-0">
                    Each row produces a single MISP attribute (e.g. one IP,
                    domain, or hash per row).
                  </p>
                </div>
              </label>
            </div>

            <!-- Object mode -->
            <div class="col-md-6">
              <label
                class="mode-card card h-100"
                :class="{ active: modelValue === 'object' }"
              >
                <input
                  class="form-check-input d-none"
                  type="radio"
                  value="object"
                  :checked="modelValue === 'object'"
                  @change="select('object')"
                />

                <div class="card-body">
                  <h6 class="mb-2">Row → Object</h6>
                  <p class="text-muted mb-0">
                    Each row produces a MISP object composed of multiple related
                    attributes.
                  </p>
                </div>
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
