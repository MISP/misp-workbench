<script setup>
import { ref, computed } from "vue";
import { authHelper } from "@/helpers";
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
  object_uuid: String,
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

function handleAttributeDeleted(attribute_uuid) {
  attributes.value = attributes.value.filter((a) => a.uuid !== attribute_uuid);
}
function handleAttributeCreated(attribute) {
  attributes.value.push(attribute);
}

function handleAttributeEnriched(attribute_uuid) {
  emit("attribute-enriched", { "attribute.uuid": attribute_uuid });
}
</script>

<style scoped>
.table {
  table-layout: fixed;
  /* as in AttributesIndex: scroll rather than squeeze the value column away */
  min-width: 40rem;
}

/*
 * The action toolbar is a fixed ~195px wide, so the 20% share it used to get
 * left it overflowing its cell and drawing over the timestamp on anything but
 * a wide screen. These widths reserve what the content needs and leave the
 * remainder to value, which is the column worth reading.
 */
.actions-col {
  width: 14rem;
}

.type-col {
  width: 6rem;
}

.timestamp-col {
  width: 12rem;
  white-space: nowrap;
}

.value {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  box-sizing: border-box;
}
</style>

<template>
  <div class="table-responsive">
    <table class="table table-striped">
      <thead>
        <tr>
          <th scope="col">value</th>
          <th scope="col" class="type-col">type</th>
          <th style="width: 22%" scope="col" class="d-none d-sm-table-cell">
            tags
          </th>
          <!-- timestamp is the first column to go: below lg there is not room
             for it and the action toolbar side by side -->
          <th scope="col" class="timestamp-col d-none d-lg-table-cell">
            timestamp
          </th>
          <th
            v-if="
              actions.view || actions.enrich || actions.update || actions.delete
            "
            scope="col"
            class="actions-col text-end"
          >
            actions
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          :key="attribute.uuid"
          v-for="attribute in attributes.filter((a) => !a.deleted)"
        >
          <td class="value">
            <CopyToClipboard :value="attribute.value" />
            {{ attribute.value }}
          </td>
          <td class="type-col">{{ attribute.type }}</td>
          <td class="d-none d-sm-table-cell">
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
          <td class="timestamp-col d-none d-lg-table-cell">
            <Timestamp :timestamp="attribute.timestamp" />
          </td>
          <td
            class="actions-col text-end"
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
  </div>
</template>
