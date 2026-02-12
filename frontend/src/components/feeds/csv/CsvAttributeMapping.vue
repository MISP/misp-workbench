<script setup>
import { computed } from "vue";
import AttributeTypeSelect from "@/components/enums/AttributeTypeSelect.vue";
import TagsSelect from "@/components/tags/TagsSelect.vue";
import { faChevronDown } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { Form, Field } from "vee-validate";
import { CsvFeedSettingsSchema } from "@/schemas/feed";

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

const csvConfig = computed({
  get: () => props.modelValue,
  set: (val) => emit("update:modelValue", val),
});

if (!csvConfig.value.properties) {
  csvConfig.value.properties = {};
}

attributeProperties.forEach((prop) => {
  if (!csvConfig.value.properties[prop.key]) {
    csvConfig.value.properties[prop.key] = {
      strategy: null,
      column: null,
      value: null,
    };
  }
});

const addMapping = () => {
  csvConfig.value.type.mappings.push({ from: "", to: "" });
};

const removeMapping = (idx) => {
  csvConfig.value.type.mappings.splice(idx, 1);
};

if (!csvConfig.value.type.mappings) {
  csvConfig.value.type.mappings = [];
}

function handleFallbackTypeChanged(type) {
  csvConfig.value.type.fallback = type;
}

function handleFixedTypeChanged(type) {
  csvConfig.value.type.value = type;
}

function handleMappingTypeChanged(type, idx) {
  csvConfig.value.type.mappings[idx].to = type;
}
</script>

<template>
  <div class="card">
    <div class="card-header">
      <h5 class="mb-0">Attribute Mapping</h5>
    </div>

    <div class="card-body">
      <Form :validation-schema="CsvFeedSettingsSchema" v-slot="{ errors }">
        <!-- VALUE COLUMN -->
        <div class="row">
          <div class="mb-3 col-md-4">
            <label class="form-label" for="csvConfig.attribute.value_column"
              >Attribute Value column</label
            >
            <Field
              class="form-select"
              as="select"
              id="csvConfig.attribute.value_column"
              name="csvConfig.attribute.value_column"
              v-model="csvConfig.value_column"
              :class="{
                'is-invalid': errors['csvConfig.attribute.value_column'],
              }"
            >
              <option
                v-for="col in columns"
                :key="col.index"
                :value="col.index"
              >
                {{ col.name }} ({{ col.index }})
              </option>
            </Field>
            <small class="text-muted">
              This column provides the attribute value.
            </small>
          </div>
          <div class="mb-3 col-md-4">
            <label class="form-label">Sample</label>
            <div class="border rounded p-2 text-truncate">
              <span
                >{{
                  rows.length > 0 ? rows[0][csvConfig.value_column] : "—"
                }}&nbsp;</span
              >
            </div>
          </div>
        </div>
        <hr />

        <!-- TYPE STRATEGY -->
        <div class="mb-3">
          <label class="form-label">Attribute Type</label>

          <div class="form-check">
            <input
              class="form-check-input"
              type="radio"
              value="fixed"
              v-model="csvConfig.type.strategy"
              id="type-fixed"
            />
            <label class="form-check-label" for="type-fixed">
              Fixed Type
            </label>
          </div>

          <div class="form-check">
            <input
              class="form-check-input"
              type="radio"
              value="column"
              v-model="csvConfig.type.strategy"
              id="type-column"
            />
            <label class="form-check-label" for="type-column">
              Type from column
            </label>
          </div>
        </div>

        <div v-if="csvConfig.type.strategy === 'column'" class="mb-3">
          <!-- COLUMN SELECT -->
          <div class="row">
            <div class="mb-3 col-md-4">
              <label class="form-label">Type column</label>
              <select class="form-select mb-3" v-model="csvConfig.type.column">
                <option disabled value="">Select column</option>
                <option v-for="col in columns" :key="col" :value="col.index">
                  {{ col.name }}
                </option>
              </select>
            </div>
            <div class="mb-3 col-md-4">
              <label class="form-label">Sample</label>
              <div class="border rounded p-2 text-truncate">
                <span
                  >{{
                    rows.length > 0 ? rows[0][csvConfig.type.column] : "—"
                  }}&nbsp;</span
                >
              </div>
            </div>
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
                    <tr
                      v-for="(mapping, idx) in csvConfig.type.mappings"
                      :key="idx"
                    >
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

                    <tr v-if="csvConfig.type.mappings.length === 0">
                      <td colspan="3" class="text-muted text-center">
                        No mappings defined
                      </td>
                    </tr>
                  </tbody>
                </table>

                <button
                  class="btn btn-sm btn-outline-primary"
                  @click="addMapping"
                >
                  + Add type mapping
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
              Used when the column value doesn’t match any mapping.
            </small>
          </div>
        </div>

        <!-- FIXED TYPE -->
        <div v-if="csvConfig.type.strategy === 'fixed'" class="mb-3 col-md-4">
          <AttributeTypeSelect
            name="csvConfig.attribute.type.value"
            @attribute-type-updated="handleFixedTypeChanged"
            :errors="errors['csvConfig.attribute.type.value']"
          />
        </div>
        <hr />

        <div class="card">
          <div class="card-header py-2">
            <button
              class="btn m-0"
              type="button"
              data-bs-toggle="collapse"
              data-bs-target="#advancedCardBody"
              aria-expanded="false"
              aria-controls="advancedCardBody"
            >
              Advanced property mappings
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
                class="row align-items-center mb-3"
              >
                <!-- LABEL -->
                <label class="col-sm-3 col-form-label">
                  {{ prop.label }}
                </label>

                <!-- CONTROLS -->
                <div class="col-sm-9">
                  <!-- STRATEGY SWITCH -->
                  <div class="d-flex align-items-center gap-3 mb-2">
                    <div class="form-check form-check-inline">
                      <input
                        class="form-check-input"
                        type="radio"
                        :name="`prop-${prop.key}`"
                        :value="null"
                        v-model="csvConfig.properties[prop.key].strategy"
                      />
                      <label class="form-check-label small text-muted"
                        >Not mapped</label
                      >
                    </div>

                    <div class="form-check form-check-inline">
                      <input
                        class="form-check-input"
                        type="radio"
                        :name="`prop-${prop.key}`"
                        value="column"
                        v-model="csvConfig.properties[prop.key].strategy"
                      />
                      <label class="form-check-label small">Column</label>
                    </div>

                    <div class="form-check form-check-inline">
                      <input
                        class="form-check-input"
                        type="radio"
                        :name="`prop-${prop.key}`"
                        value="fixed"
                        v-model="csvConfig.properties[prop.key].strategy"
                      />
                      <label class="form-check-label small">Fixed value</label>
                    </div>
                  </div>

                  <!-- COLUMN SELECT -->
                  <div class="col-md-10">
                    <div
                      class="row"
                      v-if="
                        csvConfig.properties[prop.key].strategy === 'column'
                      "
                    >
                      <div class="col-md-6">
                        <select
                          class="form-select form-select-sm"
                          v-model="csvConfig.properties[prop.key].column"
                        >
                          <option disabled value="">Select column</option>
                          <option
                            v-for="col in columns"
                            :key="col.index"
                            :value="col.index"
                          >
                            {{ col.name }}
                          </option>
                        </select>
                      </div>
                      <div class="col-md-6">
                        <code>
                          {{
                            rows.length > 0 &&
                            csvConfig.properties[prop.key].column !== null
                              ? rows[0][csvConfig.properties[prop.key].column]
                              : "—"
                          }}
                        </code>
                      </div>
                    </div>

                    <!-- FIXED VALUE INPUT -->
                    <div class="col-md-6">
                      <div
                        v-if="
                          csvConfig.properties[prop.key].strategy === 'fixed'
                        "
                      >
                        <div v-if="prop.key === 'tags'">
                          <TagsSelect
                            :modelClass="'event'"
                            :model="csvConfig.properties[prop.key].value"
                            :persist="false"
                            @update:selectedTags="
                              csvConfig.properties[prop.key].value = $event
                            "
                          />
                        </div>
                        <div v-else-if="prop.key === 'to_ids'">
                          <select
                            class="form-select form-select-sm"
                            v-model="csvConfig.properties[prop.key].value"
                          >
                            <option disabled value="">Select value</option>
                            <option :value="true">true</option>
                            <option :value="false">false</option>
                          </select>
                        </div>
                        <div v-else>
                          <input
                            v-if="prop.key !== 'tags' && prop.key !== 'to_ids'"
                            type="text"
                            class="form-control form-control-sm"
                            v-model="csvConfig.properties[prop.key].value"
                            placeholder="Enter fixed value"
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                  <small class="text-muted d-block mt-1">
                    {{ prop.help }}
                  </small>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Form>
    </div>
  </div>
</template>
