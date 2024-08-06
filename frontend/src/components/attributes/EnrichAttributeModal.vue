<script setup>
import { ref } from 'vue';
import { useModulesStore, useObjectsStore } from "@/stores";
import { storeToRefs } from 'pinia'
import UUID from "@/components/misc/UUID.vue";
import ApiError from "@/components/misc/ApiError.vue";

const props = defineProps(['attribute', 'modal']);
const emit = defineEmits(['object-created', 'attribute-enriched']);

const modulesStore = useModulesStore();
const objectsStore = useObjectsStore();
const { status, modules, modulesResponses } = storeToRefs(modulesStore);
const allModules = ref(false);
const allEnrichments = ref(false);
const enrichErrors = ref([]);


modulesStore.get({ enabled: true });

function queryModules() {
    modulesResponses.value = [];
    let selectedModules = modules.value.filter((module) => module.query);

    modulesStore.queryAll(selectedModules, props.attribute)
        .catch((error) => status.error = error);
}

function toggleAllEnrichments() {
    modulesResponses.value.forEach((moduleResults) => {
        moduleResults.response.results.Attribute.forEach((attr) => {
            attr.selected = allEnrichments.value;
        });
        moduleResults.response.results.Object.forEach((obj) => {
            obj.selected = allEnrichments.value;
        });
    });
}

function enrichAttribute() {
    let objects = [];
    let attributes = [];
    modulesResponses.value.forEach((moduleResults) => {
        if (!moduleResults.response.results) {
            return;
        }
        moduleResults.response.results.Attribute.forEach((attr) => {
            if (attr.selected) {
                attributes.push(attr);
            }
        });
        moduleResults.response.results.Object.forEach((obj) => {
            if (obj.selected) {
                objects.push(obj);
            }
        });
    });

    const promises = objects.map(object => {
        object.event_id = props.attribute.event_id;
        object.distribution = props.attribute.distribution;
        object.sharing_group_id = props.attribute.sharing_group_id;
        object.timestamp = parseInt(Date.now() / 1000);
        object.deleted = false;
        object.attributes = object.Attribute;

        for (let attribute of object.attributes) {
            attribute.event_id = props.attribute.event_id;
            attribute.distribution = props.attribute.distribution;
            attribute.sharing_group_id = props.attribute.sharing_group_id;
            attribute.timestamp = parseInt(Date.now() / 1000);
            attribute.deleted = false;
        }
        return objectsStore.create(object)
            .then(response => {
                emit('object-created', { "object": response });
            });
    });

    status.loading = true;
    Promise.all(promises)
        .then(() => {
            emit('attribute-enriched', { "attribute.id": props.attribute });
            props.modal.hide();
        })
        .catch((error) => enrichErrors.value = error)
        .finally(() => status.loading = false);
}

function toggleAllModules() {
    Object.keys(modules.value).forEach((key) => {
        modules.value[key].query = allModules.value;
    });
}
</script>

<template>
    <div :id="`enrichAttributeModal_${attribute.id}`" class="modal">
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <div class="container">
                    <div class="modal-header">
                        <h5 class="modal-title">Enrich Attribute #{{ attribute.id }}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Discard"></button>
                    </div>
                    <div class="modal-body text-start">
                        <h5>enabled modules</h5>
                        <table class="table">
                            <thead>
                                <tr>
                                    <th scope="col">name</th>
                                    <th scope="col">description</th>
                                    <th scope="col">version</th>
                                    <th scope="col">
                                        <div class="form-check float-end">
                                            <input class="form-check-input" type="checkbox" v-model="allModules"
                                                @change="toggleAllModules">
                                        </div>
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr scope="row" v-for="module in modules">
                                    <td>{{ module.name }}</td>
                                    <td>{{ module.meta.description }}</td>
                                    <td>
                                        <span class="badge badge-pill bg-info"> v{{ module.meta.version }} </span>
                                    </td>
                                    <td>
                                        <div class="form-check form-switch">
                                            <input class="form-check-input" type="checkbox" v-model="module.query"
                                                :checked="module.query">
                                        </div>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <div>
                        <button type="button" class="btn btn-outline-primary text-end"
                            @click="queryModules">Query</button>
                        <div class="text-start mt-4">
                            <div class="row">
                                <div class="col">
                                    <h5>preview enrichment results</h5>
                                </div>
                                <div class="col">
                                    <div v-if="modulesResponses.length" class="form-check float-end">
                                        <div class="form-check float-end fs-5">
                                            <label>Select All Enrichments</label>
                                            <input id="btn-check-all-enrichments" class="form-check-input"
                                                type="checkbox" v-model="allEnrichments" @change="toggleAllEnrichments">
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div v-for="moduleResults in modulesResponses">
                                <h5>{{ moduleResults.module }}</h5>
                                <div v-if="!moduleResults.response.results" class="alert alert-info" role="alert">
                                    No enrichment results available.
                                </div>
                                <div v-if="moduleResults.response.results">
                                    <div v-for="attr in moduleResults.response.results.Attribute">
                                        <div class="card mt-2" v-if="attr.uuid != attribute.uuid">
                                            <div class="card-header">
                                                Attribute <span class="badge badge-pill bg-info"> {{ attr.type }}
                                                </span>
                                                <div class="form-check float-end fs-4">
                                                    <input class="form-check-input" type="checkbox" />
                                                </div>
                                            </div>
                                            <div class="card-body">
                                                <table class="table">
                                                    <thead>
                                                        <tr>
                                                            <th scope="col">value</th>
                                                            <th scope="col">type</th>
                                                            <th scope="col">to_ids</th>
                                                            <th scope="col">disable_correlation</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        <tr scope="row">
                                                            <td>{{ attr.value }}</td>
                                                            <td>{{ attr.type }}</td>
                                                            <td>{{ attr.to_ids }}</td>
                                                            <td>{{ attr.disable_correlation }}</td>
                                                        </tr>
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>
                                    </div>
                                    <div v-for="object in moduleResults.response.results.Object">
                                        <div class="card mt-2">
                                            <div class="card-header">
                                                Object <span class="badge badge-pill bg-info"> {{ object.name }} </span>
                                                <div class="form-check float-end fs-4">
                                                    <input class="form-check-input" type="checkbox"
                                                        v-model="object.selected" />
                                                </div>
                                            </div>
                                            <div class="card-body">
                                                <div v-if="object.ObjectReference">
                                                    <h6>references:</h6>
                                                    <div v-for="reference in object.ObjectReference">
                                                        <UUID :uuid="reference.object_uuid" />
                                                        <font-awesome-icon icon="fa-solid fa-arrow-right" />
                                                        {{ reference.relationship_type }}
                                                        <font-awesome-icon icon="fa-solid fa-arrow-right" />
                                                        <UUID :uuid="reference.referenced_uuid" />
                                                    </div>
                                                </div>
                                                <table class="table">
                                                    <thead>
                                                        <tr>
                                                            <th scope="col">value</th>
                                                            <th scope="col">type</th>
                                                            <th scope="col">to_ids</th>
                                                            <th scope="col">disable_correlation</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        <tr scope="row" v-for="attribute in object.Attribute">
                                                            <td>{{ attribute.value }}</td>
                                                            <td>{{ attribute.type }}</td>
                                                            <td>{{ attribute.to_ids }}</td>
                                                            <td>{{ attribute.disable_correlation }}</td>
                                                        </tr>
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div v-if="!modulesResponses.length" class="alert alert-info" role="alert">
                                No enrichment results available.
                            </div>
                            <div v-if="status.error" class="w-100 alert alert-danger mt-3 mb-3">
                                {{ status.error }}
                            </div>
                            <div v-if="enrichErrors.length" class="w-100 alert alert-danger mt-3 mb-3">
                                <ApiError :errors="enrichErrors" />
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button id="closeModalButton" type="button" data-bs-dismiss="modal"
                        class="btn btn-secondary">Discard</button>
                    <button type="submit" @click="enrichAttribute" class="btn btn-outline-primary"
                        :class="{ 'disabled': status.loading }">
                        <span v-if="status.loading">
                            <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                        </span>
                        <span v-if="!status.loading">Enrich</span>
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>
