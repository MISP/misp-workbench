<script setup>
import { ref } from 'vue';
import DistributionLevel from "@/components/enums/DistributionLevel.vue";
import TagsIndex from "@/components/tags/TagsIndex.vue";
import { RouterLink } from "vue-router";
import DeleteAttributeModal from "@/components/attributes/DeleteAttributeModal.vue";


const props = defineProps(['object_id', 'attributes']);
const attributes = ref(props.attributes);

function handleAttributesUpdated(attribute) {
    attributes.value = attributes.value.filter(a => a.id !== attribute.attribute_id);
}
</script>

<template>
    <table class="table table-striped">
        <thead>
            <tr>
                <th style="width: 30%" scope="col">value</th>
                <th style="width: 30%" scope="col" class="d-none d-sm-table-cell">tags</th>
                <th style="width: 10%" scope="col" class="d-none d-sm-table-cell">category</th>
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
                <td class="d-none d-sm-table-cell">{{ attribute.category }}</td>
                <td>{{ attribute.type }}</td>
                <td class="d-none d-sm-table-cell">{{ attribute.timestamp }}</td>
                <td class="d-none d-sm-table-cell">
                    <DistributionLevel :distribution_level_id=attribute.distribution />
                </td>
                <td class="text-end">
                    <div :class="{ 'btn-group-vertical': $isMobile, 'btn-group': !$isMobile }" aria-label="Attribute Actions">
                        <button type="button" class="btn btn-outline-danger" data-bs-toggle="modal"
                            :data-bs-target="'#deleteAttributeModal-' + attribute.id">
                            <font-awesome-icon icon="fa-solid fa-trash" />
                        </button>
                        <RouterLink :to="`/attributes/update/${attribute.id}`" tag="button" class="btn btn-outline-primary">
                            <font-awesome-icon icon="fa-solid fa-pen" />
                        </RouterLink>
                        <RouterLink :to="`/attributes/${attribute.id}`" tag="button" class="btn btn-outline-primary">
                            <font-awesome-icon icon="fa-solid fa-eye" />
                        </RouterLink>
                    </div>
                </td>
                <DeleteAttributeModal @attribute-deleted="handleAttributesUpdated" :attribute_id="attribute.id" />
            </tr>
        </tbody>
    </table>
</template>