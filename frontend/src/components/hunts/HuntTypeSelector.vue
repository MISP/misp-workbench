<script setup>
defineProps({
  modelValue: {
    type: String,
    required: true,
  },
});

const emit = defineEmits(["update:modelValue"]);

const huntTypes = [
  {
    value: "opensearch",
    label: "OpenSearch query",
    description: "Lucene query against attributes, events, or correlations.",
    icon: "bi bi-search",
  },
  {
    value: "mitre-attack-pattern",
    label: "MITRE ATT&CK",
    description:
      "Match events or attributes tagged with selected ATT&CK techniques.",
    icon: "bi bi-diagram-2",
  },
  {
    value: "cpe",
    label: "CPE vuln lookup",
    description: "Track CVEs affecting a given CPE via vulnerability.circl.lu.",
    icon: "bi bi-shield-exclamation",
  },
  {
    value: "rulezet",
    label: "Rulezet vuln check",
    description: "Detection rules available for a given CVE.",
    icon: "bi bi-bug",
  },
];

function select(value) {
  emit("update:modelValue", value);
}
</script>

<style scoped>
.hunt-type-card {
  cursor: pointer;
  border: 1px solid var(--bs-border-color);
  transition: all 0.15s ease-in-out;
}

.hunt-type-card:hover {
  border-color: var(--bs-primary);
  box-shadow: 0 0 0 1px rgba(13, 110, 253, 0.25);
}

.hunt-type-card.active {
  border-color: var(--bs-primary);
  background-color: rgba(13, 110, 253, 0.05);
}

.hunt-type-card i {
  color: var(--bs-primary);
}
</style>

<template>
  <div class="hunt-type-selector">
    <div class="row g-2">
      <div v-for="type in huntTypes" :key="type.value" class="col-md-6">
        <label
          class="hunt-type-card card h-100"
          :class="{ active: modelValue === type.value }"
        >
          <input
            class="form-check-input d-none"
            type="radio"
            name="huntType"
            :value="type.value"
            :checked="modelValue === type.value"
            @change="select(type.value)"
          />

          <div class="card-body p-3">
            <div class="d-flex align-items-center mb-1">
              <i :class="type.icon" class="me-2 fs-5"></i>
              <h6 class="mb-0">{{ type.label }}</h6>
            </div>
            <p class="text-muted small mb-0">{{ type.description }}</p>
          </div>
        </label>
      </div>
    </div>
  </div>
</template>
