<script setup>
import { ref } from 'vue';
import DistributionLevel from "@/components/enums/DistributionLevel.vue";
import TagsIndex from "@/components/tags/TagsIndex.vue";
import Timestamp from "@/components/misc/Timestamp.vue";
import AttributeActions from "@/components/attributes/AttributeActions.vue";

const props = defineProps(['object_id', 'attributes']);
const emit = defineEmits(['attribute-created', 'attribute-updated', 'attribute-deleted', 'object-created', 'attribute-enriched']);

const attributes = ref(props.attributes);

function handleAttributeDeleted(attribute_id) {
    attributes.value = attributes.value.filter(a => a.id !== attribute_id);
}
function handleAttributeCreated(attribute) {
    attributes.value.push(attribute);
}

function handleAttributeEnriched(attribute_id) {
    emit('attribute-enriched', { "attribute.id": attribute_id });
}
</script>

<template>
    <table class="table table-striped">
        <thead>
            <tr>
                <th style="width: 30%" scope="col">value</th>
                <th style="width: 20%" scope="col" class="d-none d-sm-table-cell">tags</th>
                <th style="width: 10%" scope="col">type</th>
                <th style="width: 10%" scope="col" class="d-none d-sm-table-cell">timestamp</th>
                <th style="width: 10%" scope="col" class="d-none d-sm-table-cell">distribution</th>
                <th style="width: 20%" scope="col" class="text-end">actions</th>
            </tr>
        </thead>
        <tbody>
            <tr :key="attribute.id" v-for="attribute in attributes.filter(attr => !attr.deleted)">
                <td>{{ attribute.value }}</td>
                <td class="d-none d-sm-table-cell">
                    <TagsIndex :tags="attribute.tags" />
                </td>
                <td>{{ attribute.type }}</td>
                <td class="d-none d-sm-table-cell">
                    <Timestamp :timestamp="attribute.timestamp" />
                </td>
                <td class="d-none d-sm-table-cell">
                    <DistributionLevel :distribution_level_id=attribute.distribution />
                </td>
                <td class="text-end">
                    <AttributeActions :attribute="attribute" @attribute-deleted="handleAttributeDeleted"
                        @attribute-created="handleAttributeCreated" @attribute-enriched="handleAttributeEnriched" />
                </td>
            </tr>
        </tbody>
    </table>
</template>