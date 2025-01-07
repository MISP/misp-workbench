<script setup>
import { ref, onMounted, computed, nextTick } from 'vue';
import { tagHelper } from "@/helpers";
import TomSelect from 'tom-select';
import 'tom-select/dist/css/tom-select.bootstrap5.min.css';
import { fetchWrapper } from "@/helpers";

const selectElement = ref(null);

const baseUrl = `${import.meta.env.VITE_API_URL}/taxonomies`;
onMounted(() => {
    new TomSelect(selectElement.value, {
        create: false,
        placeholder: 'Select a tag...',
        valueField: 'name',
        labelField: 'name',
        searchField: 'name',
        options: [],
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
                    console.log(tags);
                    callback(tags);
                }).catch(() => {
                    callback();
                });
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
        }
    });
});
</script>

<template>
    <select ref="selectElement" multiple></select>
</template>
