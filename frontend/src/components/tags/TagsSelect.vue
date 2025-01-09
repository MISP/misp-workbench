<script setup>
import { ref, onMounted } from 'vue';
import { tagHelper } from "@/helpers";
import TomSelect from 'tom-select';
import { fetchWrapper } from "@/helpers";
import { useAttributesStore, useEventsStore } from "@/stores";

const props = defineProps({
    modelClass: {
        type: String,
        required: true,
    },
    model: {
        type: Object,
        required: true,
    },
    tags: {
        type: Array,
        default: () => [],
    },
});

const eventsStore = useEventsStore();
const attributesStore = useAttributesStore();

const selectElement = ref(null);
const taxonomiesBaseUrl = `${import.meta.env.VITE_API_URL}/taxonomies`;

onMounted(() => {
    new TomSelect(selectElement.value, {
        create: false,
        placeholder: 'Click to add a tag...',
        valueField: 'name',
        labelField: 'name',
        searchField: 'name',
        items: ["tlp:red"],
        plugins: {
            remove_button: {
                title: 'Remove this tag',
            }
        },
        preload: true,
        load: function (query, callback) {
            fetchWrapper
                .get(taxonomiesBaseUrl + "/?" + new URLSearchParams({
                    enabled: true,
                    query: query,
                }).toString())
                .then((response) => {
                    let tags = [];
                    response.items.map((taxonomy) => {
                        taxonomy.predicates.map((predicate) => {
                            tags.push({
                                id: predicate.id,
                                name: tagHelper.getTag(taxonomy.namespace, predicate.value),
                                color: tagHelper.getContrastColor(predicate.colour),
                                backgroundColor: predicate.colour,
                            });
                        });
                    });
                    callback(tags);
                }).catch(() => {
                    callback();
                });
        },
        onLoad() {
            // add already selected tags
            // using `items` doest not work because options do not exist yet
            // TODO: find a better way to do this, as this is triggering onItemAdd event
            selectElement.value.tomselect.setValue(props.tags.map(tag => tag.name), false);
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
            console.log("tag added", tag);
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


</script>

<template>
    <select ref="selectElement" multiple>
    </select>
</template>
