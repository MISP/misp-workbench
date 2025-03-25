<script setup>
import { ref, computed } from "vue";
import { authHelper } from "@/helpers";
import DistributionLevel from "@/components/enums/DistributionLevel.vue";
import TagsSelect from "@/components/tags/TagsSelect.vue";
import Timestamp from "@/components/misc/Timestamp.vue";
import CopyToClipboard from "@/components/misc/CopyToClipboard.vue";
import AttributeActions from "@/components/attributes/AttributeActions.vue";
import TagsIndex from "../tags/TagsIndex.vue";
import { useAuthStore } from "@/stores";
import { storeToRefs } from "pinia";

const authStore = useAuthStore();
const { scopes } = storeToRefs(authStore);

const props = defineProps({
  object_id: Number,
  attributes: Array,
  default_actions: {
    type: Object,
    default: () => ({}),
  },
});

const actions = computed(() => ({
  view:
    props.default_actions.view ??
    authHelper.hasScope(scopes.value, "attributes:view"),
  enrich:
    props.default_actions.enrich ??
    authHelper.hasScope(scopes.value, "attributes:enrich"),
  update:
    props.default_actions.update ??
    authHelper.hasScope(scopes.value, "attributes:update"),
  delete:
    props.default_actions.delete ??
    authHelper.hasScope(scopes.value, "attributes:delete"),
  tag:
    props.default_actions.tag ??
    authHelper.hasScope(scopes.value, "attributes:tag"),
}));

const emit = defineEmits([
  "attribute-created",
  "attribute-updated",
  "attribute-deleted",
  "attribute-enriched",
]);

const attributes = ref(props.attributes);

function handleAttributeDeleted(attribute_id) {
  attributes.value = attributes.value.filter((a) => a.id !== attribute_id);
}
function handleAttributeCreated(attribute) {
  attributes.value.push(attribute);
}

function handleAttributeEnriched(attribute_id) {
  emit("attribute-enriched", { "attribute.id": attribute_id });
}
</script>

<style scoped>
.table {
  table-layout: fixed;
}

.value {
  width: 30%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  box-sizing: border-box;
}
</style>

<template>
  <table class="table table-striped">
    <thead>
      <tr>
        <th scope="col">value</th>
        <th style="width: 400px" scope="col" class="d-none d-sm-table-cell">
          tags
        </th>
        <th scope="col">type</th>
        <th scope="col" class="d-none d-sm-table-cell">timestamp</th>
        <th scope="col" class="d-none d-sm-table-cell">distribution</th>
        <th
          v-if="
            actions.view || actions.enrich || actions.update || actions.delete
          "
          scope="col"
          class="text-end"
        >
          actions
        </th>
      </tr>
    </thead>
    <tbody>
      <tr
        :key="attribute.id"
        v-for="attribute in attributes.filter((a) => !a.deleted)"
      >
        <td class="value">
          <CopyToClipboard :value="attribute.value" />
          {{ attribute.value }}
        </td>
        <td style="width: 20%" class="d-none d-sm-table-cell">
          <TagsIndex
            v-if="!actions.tag"
            :tags="attribute.tags || attribute.AttributeTag || []"
          />
          <TagsSelect
            v-if="actions.tag"
            :modelClass="'attribute'"
            :model="attribute"
            :selectedTags="attribute.tags || attribute.AttributeTag || []"
          />
        </td>
        <td style="width: 10%">{{ attribute.type }}</td>
        <td style="width: 10%" class="d-none d-sm-table-cell">
          <Timestamp :timestamp="attribute.timestamp" />
        </td>
        <td style="width: 10%" class="d-none d-sm-table-cell">
          <DistributionLevel :distribution_level_id="attribute.distribution" />
        </td>
        <td
          style="width: 20%"
          class="text-end"
          v-if="
            actions.view || actions.enrich || actions.update || actions.delete
          "
        >
          <AttributeActions
            :attribute="attribute"
            :default_actions="actions"
            @attribute-deleted="handleAttributeDeleted"
            @attribute-created="handleAttributeCreated"
            @attribute-enriched="handleAttributeEnriched"
          />
        </td>
      </tr>
    </tbody>
  </table>
</template>
