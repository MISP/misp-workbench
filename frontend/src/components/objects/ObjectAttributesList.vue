<script setup>
import { ref } from 'vue';
import DistributionLevel from "@/components/enums/DistributionLevel.vue";
import TagsIndex from "@/components/tags/TagsIndex.vue";
import { RouterLink } from "vue-router";
import Timestamp from "@/components/misc/Timestamp.vue";
import DeleteAttributeModal from "@/components/attributes/DeleteAttributeModal.vue";
import AttributeActions from "@/components/attributes/AttributeActions.vue";

const props = defineProps(['object_id', 'attributes']);
const attributes = ref(props.attributes);

function handleAttributesUpdated(attribute_id) {
    attributes.value = attributes.value.filter(a => a.id !== attribute_id);
}
</script>

<template>
    <table class="table table-striped">
        <thead>
            <tr>
                <th style="width: 30%" scope="col">value</th>
                <th style="width: 30%" scope="col" class="d-none d-sm-table-cell">tags</th>
                <th style="width: 10%" scope="col">type</th>
                <th style="width: 10%" scope="col" class="d-none d-sm-table-cell">timestamp</th>
                <th style="width: 10%" scope="col" class="d-none d-sm-table-cell">distribution</th>
                <th style="width: 10%" scope="col" class="text-end">actions</th>
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
                    <AttributeActions :attribute="attribute" @attribute-deleted="handleAttributesUpdated" />
                </td>
            </tr>
        </tbody>
    </table>
</template>