<script setup>
import { ref, reactive, watch } from "vue";
import TagsSelect from "@/components/tags/TagsSelect.vue";
import OrganisationsMultiSelect from "@/components/organisations/OrganisationsMultiSelect.vue";
import AttributeTypeMultiSelect from "@/components/enums/AttributeTypeMultiSelect.vue";
import ObjectTemplateMultiSelect from "@/components/enums/ObjectTemplateMultiSelect.vue";

const props = defineProps({
  modelValue: { type: [Object, null], default: () => ({}) },
  modelClass: { type: String, default: "event" },
  resourceType: { type: String, default: "event" },
});
const emit = defineEmits(["update:modelValue"]);

const mode = ref("basic");

const basic = reactive({
  tags: { enabled: false, tags: [] },
  orgs: { enabled: false, orgs: [] },
  types: { enabled: false, types: [] },
  templates: { enabled: false, templates: [] },
});

const advancedJson = ref("");
const jsonError = ref(null);

const existing = props.modelValue ?? {};
if (Array.isArray(existing.tags) && existing.tags.length) {
  basic.tags.enabled = true;
  basic.tags.tags = [...existing.tags];
}
if (Array.isArray(existing.orgs) && existing.orgs.length) {
  basic.orgs.enabled = true;
  basic.orgs.orgs = [...existing.orgs];
}
if (Array.isArray(existing.types) && existing.types.length) {
  basic.types.enabled = true;
  basic.types.types = [...existing.types];
}
if (Array.isArray(existing.templates) && existing.templates.length) {
  basic.templates.enabled = true;
  basic.templates.templates = [...existing.templates];
}
if (Object.keys(existing).length) {
  advancedJson.value = JSON.stringify(existing, null, 2);
}

watch(
  [mode, basic, advancedJson],
  () => {
    let rules = {};

    if (mode.value === "basic") {
      if (basic.tags.enabled && basic.tags.tags.length > 0) {
        rules.tags = basic.tags.tags;
      }
      if (basic.orgs.enabled && basic.orgs.orgs.length > 0) {
        rules.orgs = basic.orgs.orgs;
      }
      if (
        props.resourceType === "attribute" &&
        basic.types.enabled &&
        basic.types.types.length > 0
      ) {
        rules.types = basic.types.types;
      }
      if (
        props.resourceType === "object" &&
        basic.templates.enabled &&
        basic.templates.templates.length > 0
      ) {
        rules.templates = basic.templates.templates;
      }
      jsonError.value = null;
    } else {
      try {
        rules = advancedJson.value ? JSON.parse(advancedJson.value) : {};
        jsonError.value = null;
      } catch (e) {
        jsonError.value = e.message;
        return;
      }
    }
    emit("update:modelValue", rules);
  },
  { deep: true },
);
</script>

<template>
  <div>
    <div class="mb-3">
      <div class="form-check form-check-inline">
        <input
          class="form-check-input"
          type="radio"
          :name="`filterMode-${$.uid}`"
          value="basic"
          v-model="mode"
          :id="`filterBasic-${$.uid}`"
        />
        <label class="form-check-label" :for="`filterBasic-${$.uid}`">
          Basic
        </label>
      </div>
      <div class="form-check form-check-inline">
        <input
          class="form-check-input"
          type="radio"
          :name="`filterMode-${$.uid}`"
          value="advanced"
          v-model="mode"
          :id="`filterAdvanced-${$.uid}`"
        />
        <label class="form-check-label" :for="`filterAdvanced-${$.uid}`">
          Advanced (JSON)
        </label>
      </div>
    </div>

    <div v-if="mode === 'basic'" class="border rounded p-3">
      <div class="form-check mb-3">
        <input
          class="form-check-input"
          type="checkbox"
          v-model="basic.tags.enabled"
          :id="`filterTags-${$.uid}`"
        />
        <label class="form-check-label" :for="`filterTags-${$.uid}`">
          Only fire when matching specific tags
        </label>
        <div class="row g-2 mt-2" v-if="basic.tags.enabled">
          <TagsSelect
            :modelClass="modelClass"
            :model="basic.tags.tags"
            :persist="false"
            @update:selectedTags="basic.tags.tags = $event"
          />
        </div>
      </div>

      <div class="form-check mb-3">
        <input
          class="form-check-input"
          type="checkbox"
          v-model="basic.orgs.enabled"
          :id="`filterOrgs-${$.uid}`"
        />
        <label class="form-check-label" :for="`filterOrgs-${$.uid}`">
          Only fire for specific organisations
        </label>
        <div class="row g-2 mt-2" v-if="basic.orgs.enabled">
          <OrganisationsMultiSelect
            :selectedOrgs="basic.orgs.orgs"
            @update:selectedOrgs="basic.orgs.orgs = $event"
          />
        </div>
      </div>

      <div v-if="resourceType === 'attribute'" class="form-check mb-0">
        <input
          class="form-check-input"
          type="checkbox"
          v-model="basic.types.enabled"
          :id="`filterTypes-${$.uid}`"
        />
        <label class="form-check-label" :for="`filterTypes-${$.uid}`">
          Only fire for specific attribute types
        </label>
        <div class="row g-2 mt-2" v-if="basic.types.enabled">
          <AttributeTypeMultiSelect
            :selected="basic.types.types"
            @update:selected="basic.types.types = $event"
          />
        </div>
      </div>

      <div v-if="resourceType === 'object'" class="form-check mb-0">
        <input
          class="form-check-input"
          type="checkbox"
          v-model="basic.templates.enabled"
          :id="`filterTemplates-${$.uid}`"
        />
        <label class="form-check-label" :for="`filterTemplates-${$.uid}`">
          Only fire for specific object templates
        </label>
        <div class="row g-2 mt-2" v-if="basic.templates.enabled">
          <ObjectTemplateMultiSelect
            :selected="basic.templates.templates"
            @update:selected="basic.templates.templates = $event"
          />
        </div>
      </div>
    </div>

    <div v-else>
      <textarea
        class="form-control font-monospace small"
        rows="6"
        v-model="advancedJson"
        spellcheck="false"
        placeholder='{"tags": ["tlp:red"], "orgs": ["CIRCL"]}'
      />
      <div v-if="jsonError" class="text-danger small mt-1">
        Invalid JSON: {{ jsonError }}
      </div>
      <div class="alert alert-info small mt-2 mb-0">
        Supported keys:
        <code>tags</code> (array of tag names), <code>orgs</code> (array of
        organisation names)<span v-if="resourceType === 'attribute'"
          >, <code>types</code> (array of attribute types)</span
        ><span v-if="resourceType === 'object'"
          >, <code>templates</code> (array of object template names)</span
        >.
      </div>
    </div>
  </div>
</template>
