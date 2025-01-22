<script setup>
import { ref, onMounted, nextTick } from 'vue';
import { tagHelper } from "@/helpers";
import TomSelect from 'tom-select';
import { useTagsStore, useAttributesStore, useEventsStore } from "@/stores";

const props = defineProps({
    modelClass: {
        type: String,
        required: true,
    },
    model: {
        type: Object,
        required: true,
    },
    selectedTags: {
        type: Array,
        default: () => [],
    },
    tags: {
        type: Array,
        default: () => [],
    },
    taxonomies: {
        type: Object,
        default: () => { },
    },
});
const tagsStore = useTagsStore();
const eventsStore = useEventsStore();
const attributesStore = useAttributesStore();

const selectElement = ref(null);

onMounted(() => {
    let enabledTags = [];
    tagsStore.get().then((response) => {
        response.items.map((tag) => {
            enabledTags.push({
                id: tag.id,
                name: tag.name,
                color: tagHelper.getContrastColor(tag.colour),
                backgroundColor: tag.colour,
            });
        });

        new TomSelect(selectElement.value, {
            create: false,
            placeholder: 'Click to add a tag...',
            valueField: 'name',
            labelField: 'name',
            searchField: 'name',
            options: enabledTags,
            items: props.selectedTags.map(tag => tag.name),
            plugins: {
                remove_button: {
                    title: 'Remove this tag',
                }
            },
            render: {
                option: function (data, escape) {
                    return '<span class="badge mx-1 tag" style="color: ' + escape(data.color) + '; background-color: ' + escape(data.backgroundColor) + '" title="' + escape(data.name) + '">' +
                        escape(data.name) +
                        '</span>';
                },
                item: function (data, escape) {
                    return '<span class="badge mx-1 tag" style="color: ' + escape(data.color) + '; background-color: ' + escape(data.backgroundColor) + '" title="' + escape(data.name) + '">' +
                        escape(data.name) +
                        '</span>';
                }
            },
            onItemRemove: function (tag) {
                if (props.modelClass == "event") {
                    eventsStore.untag(props.model.id, tag);
                    return;
                }
                if (props.modelClass == "attribute") {
                    attributesStore.untag(props.model.id, tag);
                    return;
                }
            },
            onItemAdd: function (tag) {
                if (props.modelClass == "event") {
                    eventsStore.tag(props.model.id, tag);
                    return;
                }
                if (props.modelClass == "attribute") {
                    attributesStore.tag(props.model.id, tag);
                    return;
                }
            },
        });

    });

});
</script>

<template>
    <select ref="selectElement" multiple>
    </select>
</template>
