<script setup>
import { ref, onMounted, computed, nextTick } from 'vue';
import { tagHelper } from "@/helpers";
import TomSelect from 'tom-select';
import 'tom-select/dist/css/tom-select.bootstrap5.min.css';
import { fetchWrapper } from "@/helpers";

import { useEventsStore } from "@/stores";
import { storeToRefs } from 'pinia'
import { faCropSimple } from '@fortawesome/free-solid-svg-icons';

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
const { status } = storeToRefs(eventsStore);

const selectElement = ref(null);

const baseUrl = `${import.meta.env.VITE_API_URL}/taxonomies`;

onMounted(() => {
    new TomSelect(selectElement.value, {
        create: false,
        placeholder: 'Click to add a tag...',
        valueField: 'name',
        labelField: 'name',
        searchField: 'name',
        options: [],
        plugins: {
            remove_button: {
                title: 'Remove this tag',
            }
        },
        preload: true,
        load: function (query, callback) {
            fetchWrapper
                .get(baseUrl + "/?" + new URLSearchParams({
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
            console.log(props.tags);
            for (let tag of props.tags) {
                selectElement.value.tomselect.addItem(tag.name);
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
        },
        onItemAdd: function (tag) {
            if (props.modelClass == "event") {
                eventsStore.tag(props.model.id, tag);
                return;
            }
        },
    });

    // force load all enabled taxonomies
    nextTick(() => {
        // selectElement.value.tomselect.load('');

        // // add already selected tags

    });
});


</script>

<template>
    <select ref="selectElement" multiple>
    </select>
</template>
