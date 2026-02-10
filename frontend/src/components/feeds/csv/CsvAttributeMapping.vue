<script setup>
import AttributeTypeSelect from "@/components/enums/AttributeTypeSelect.vue";
import { faChevronDown } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

const props = defineProps({
  modelValue: {
    type: Object,
    required: true,
  },
  rows: {
    type: Array,
    default: () => [],
  },
  columns: {
    type: Array,
    required: true,
  },
});

const attributeProperties = [
  {
    key: "timestamp",
    label: "timestamp",
    help: "Unix timestamp or ISO8601 date",
  },
  {
    key: "tags",
    label: "tags",
    help: "comma-separated list of tags",
  },
  {
    key: "to_ids",
    label: "to_ids",
    help: "whether the attribute should be marked as to_ids (true/false)",
  },
  {
    key: "comment",
    label: "comment",
    help: "attribute description",
  },
  {
    key: "first_seen",
    label: "first_seen",
    help: "Unix timestamp or ISO8601 date",
  },
  {
    key: "last_seen",
    label: "last_seen",
    help: "Unix timestamp or ISO8601 date",
  },
];

const emit = defineEmits(["update:modelValue"]);

const config = computed({
  get: () => props.modelValue,
  set: (val) => emit("update:modelValue", val),
});

if (!config.value.properties) {
  config.value.properties = {};
}

for (const prop of attributeProperties) {
  if (config.value.properties[prop.key] === undefined) {
    config.value.properties[prop.key] = "";
  }
}

const addMapping = () => {
  config.value.type.mappings.push({ from: "", to: "" });
};

const removeMapping = (idx) => {
  config.value.type.mappings.splice(idx, 1);
};

if (!config.value.type.mappings) {
  config.value.type.mappings = [];
}

function handleFallbackTypeChanged(type) {
  config.value.type.fallback = type;
}

function handleFixedTypeChanged(type) {
  config.value.type.value = type;
}

function handleMappingTypeChanged(type, idx) {
  config.value.type.mappings[idx].to = type;
}
</script>

<template>
  <div class="card">
    <div class="card-header">
      <h5 class="mb-0">Attribute Mapping</h5>
    </div>

    <div class="card-body">
      <!-- VALUE COLUMN -->
      <div class="row">
        <div class="mb-3 col-md-4">
          <label class="form-label">attribute value column</label>
          <select class="form-select" v-model="config.value_column">
            <option disabled value="">Select column</option>
            <option v-for="col in columns" :key="col" :value="col">
              {{ col }}
            </option>
          </select>
          <small class="text-muted">
            This column provides the attribute value.
          </small>
        </div>
        <div class="mb-3 col-md-4">
          <label class="form-label">sample</label>
          <div class="border rounded p-2 text-truncate">
            <span
              >{{
                rows.length > 0 && config.value_column
                  ? rows[0][columns.indexOf(config.value_column)]
                  : "—"
              }}&nbsp;</span
            >
          </div>
        </div>
      </div>
      <hr />

      <!-- TYPE STRATEGY -->
      <div class="mb-3">
        <label class="form-label">attribute type</label>

        <div class="form-check">
          <input
            class="form-check-input"
            type="radio"
            value="fixed"
            v-model="config.type.strategy"
            id="type-fixed"
          />
          <label class="form-check-label" for="type-fixed"> fixed type </label>
        </div>

        <div class="form-check">
          <input
            class="form-check-input"
            type="radio"
            value="column"
            v-model="config.type.strategy"
            id="type-column"
          />
          <label class="form-check-label" for="type-column">
            type from column
          </label>
        </div>
      </div>

      <div v-if="config.type.strategy === 'column'" class="mb-3">
        <!-- COLUMN SELECT -->
        <div class="mb-3 col-md-4">
          <label class="form-label">Type column</label>
          <select class="form-select mb-3" v-model="config.type.column">
            <option disabled value="">select column</option>
            <option v-for="col in columns" :key="col" :value="col">
              {{ col }}
            </option>
          </select>
        </div>

        <!-- MAPPING TABLE -->
        <div class="card">
          <div class="card-header py-2">
            <button
              class="btn btn-sm"
              type="button"
              data-bs-toggle="collapse"
              data-bs-target="#valueMappingCardBody"
              aria-expanded="false"
              aria-controls="valueMappingCardBody"
            >
              Value mapping (optional)
              <FontAwesomeIcon :icon="faChevronDown" class="ms-1" />
            </button>
          </div>

          <div class="collapse collapsed" id="valueMappingCardBody">
            <div class="card-body">
              <table class="table table-sm align-middle">
                <thead>
                  <tr>
                    <th>CSV type</th>
                    <th>MISP type</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(mapping, idx) in config.type.mappings" :key="idx">
                    <td>
                      <input
                        type="text"
                        class="form-control form-control-sm"
                        v-model="mapping.from"
                        placeholder="e.g. ip address"
                      />
                    </td>
                    <td>
                      <AttributeTypeSelect
                        :name="`type-mapping-${idx}`"
                        @attribute-type-updated="
                          (type) => handleMappingTypeChanged(type, idx)
                        "
                      />
                    </td>
                    <td class="text-end">
                      <button
                        class="btn btn-sm btn-outline-danger"
                        @click="removeMapping(idx)"
                      >
                        ✕
                      </button>
                    </td>
                  </tr>

                  <tr v-if="config.type.mappings.length === 0">
                    <td colspan="3" class="text-muted text-center">
                      no mappings defined
                    </td>
                  </tr>
                </tbody>
              </table>

              <button
                class="btn btn-sm btn-outline-primary"
                @click="addMapping"
              >
                + add type mapping
              </button>
            </div>
          </div>
        </div>

        <!-- FALLBACK -->
        <div class="mt-3 col-md-4">
          <label class="form-label">Fallback type</label>
          <AttributeTypeSelect
            name="fallback-type-mapping"
            @attribute-type-updated="handleFallbackTypeChanged"
          />
          <small class="text-muted">
            used when the column value doesn’t match any mapping.
          </small>
        </div>
      </div>

      <!-- FIXED TYPE -->
      <div v-if="config.type.strategy === 'fixed'" class="mb-3 col-md-4">
        <AttributeTypeSelect
          name="fixed-type-mapping"
          @attribute-type-updated="handleFixedTypeChanged"
        />
      </div>
      <hr />

      <div class="card">
        <div class="card-header py-2">
          <button
            class="btn btn-sm"
            type="button"
            data-bs-toggle="collapse"
            data-bs-target="#advancedCardBody"
            aria-expanded="false"
            aria-controls="advancedCardBody"
          >
            Advanced attribute fields mappings
            <FontAwesomeIcon :icon="faChevronDown" class="ms-1" />
          </button>
        </div>

        <div class="collapse collapsed" id="advancedCardBody">
          <div class="card-body">
            <div class="text-muted small mb-3">
              Optionally map CSV columns to additional attribute properties.
            </div>

            <div
              v-for="prop in attributeProperties"
              :key="prop.key"
              class="row align-items-start mb-3"
            >
              <!-- LABEL -->
              <label class="col-sm-2 col-form-label">
                {{ prop.label }}
              </label>

              <!-- INPUT -->
              <div class="col-sm-6">
                <select
                  class="form-select"
                  v-model="config.properties[prop.key]"
                >
                  <option value="">— not mapped —</option>
                  <option v-for="col in columns" :key="col" :value="col">
                    {{ col }}
                  </option>
                </select>

                <small class="text-muted">
                  {{ prop.help }}
                </small>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
