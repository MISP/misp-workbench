<script setup>
import { Field } from "vee-validate";

defineProps(["name", "attribute_type", "errors"]);
const emit = defineEmits(["attribute-value-changed"]);

function handleValueChange(event) {
  emit("attribute-value-changed", event.target.value);
}
</script>

<template>
  <div>
    <Field
      v-if="!attribute_type.sane_default"
      class="form-control"
      id="attribute.value"
      name="attribute.value"
      :class="{ 'is-invalid': errors }"
      @change="handleValueChange"
    >
    </Field>

    <!-- If the attribute type has sane_default, change input to a datalist -->
    <Field
      v-if="attribute_type.sane_default"
      class="form-control"
      list="objectAttributeSaneDefaultOptions"
      id="objectAttributeSaneDefaultSelect"
      :name="name"
      :class="{ 'is-invalid': errors }"
      @change="handleValueChange"
      placeholder="Type to search..."
    >
    </Field>
    <datalist id="objectAttributeSaneDefaultOptions">
      <option v-for="option in attribute_type.sane_default">
        {{ option }}
      </option>
    </datalist>
  </div>
</template>
