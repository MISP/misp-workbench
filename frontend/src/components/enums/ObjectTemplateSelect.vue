<script setup>
import { Field } from "vee-validate";
import { useObjectsStore } from "@/stores";
import { storeToRefs } from "pinia";
import { computed } from "vue";

const props = defineProps(["name", "selected", "errors"]);
const emit = defineEmits(["object-template-updated"]);

const objectsStore = useObjectsStore();
const { objectTemplates } = storeToRefs(objectsStore);

objectsStore.getObjectTemplates();

const selectedName = computed(() => {
  if (!props.selected?.uuid) return "";
  const tpl = objectTemplates.value.find((t) => t.uuid === props.selected.uuid);
  return tpl?.name || "";
});

function handleInput(event) {
  const value = event.target.value;

  const match = objectTemplates.value.find(
    (t) => t.name.toLowerCase() === value.toLowerCase(),
  );

  if (match) {
    emit("object-template-updated", match.uuid);
  }
}
</script>

<template>
  <Field
    class="form-control"
    list="objectTemplateOptions"
    :name="name"
    :class="{ 'is-invalid': errors }"
    placeholder="Search object templates…"
    :value="selectedName"
    @input="handleInput"
  />

  <datalist id="objectTemplateOptions">
    <option
      v-for="template in objectTemplates"
      :key="template.uuid"
      :value="template.name"
    />
  </datalist>
</template>
