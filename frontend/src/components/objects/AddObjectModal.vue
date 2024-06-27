<script setup>

import { ref } from 'vue';
import { useObjectsStore } from "@/stores";
import { storeToRefs } from 'pinia'
import { ObjectSchema } from "@/schemas/object";
import { DISTRIBUTION_LEVEL } from "@/helpers/constants";
import DistributionLevelSelect from "@/components/enums/DistributionLevelSelect.vue";
import ObjectMetaCategorySelect from "@/components/enums/ObjectMetaCategorySelect.vue";
import ObjectTemplateSelect from "@/components/enums/ObjectTemplateSelect.vue";
import AddObjectForm from "@/components/objects/AddObjectForm.vue";
import AddObjectPreview from "@/components/objects/AddObjectPreview.vue";
import { Form, Field } from "vee-validate";


const objectsStore = useObjectsStore();
const { status } = storeToRefs(objectsStore);

const props = defineProps(['event_id']);
const emit = defineEmits(['object-created']);

const object = ref({
    distribution: DISTRIBUTION_LEVEL.INHERIT_EVENT,
    meta_category: "network",
    template_uuid: null,
    template: null,
    attributes: []
});

const activeTemplate = ref({});

function onSubmit(values, { setErrors }) {
    return objectsStore
        .create(object.value)
        .then((response) => {
            emit('object-created', { "object": response });
            document.getElementById('closeModalButton').click();
        })
        .catch((error) => setErrors({ apiError: error }));
}

function onClose() {
    object.value = {
        distribution: DISTRIBUTION_LEVEL.INHERIT_EVENT,
        meta_category: "network",
        template_uuid: null,
        template: null
    };
}

function handleDistributionLevelUpdated(distributionLevelId) {
    object.value.distribution = parseInt(distributionLevelId);
}

function handleObjectMetaCategoryUpdated(metaCategory) {
    object.value.meta_category = metaCategory;
}

function handleObjectTemplateUpdated(templateUuid) {
    object.value.template_uuid = templateUuid;
    activeTemplate.value = objectsStore.getObjectTemplateByUuid(templateUuid);
    document.getElementById('attributes-tab').click();
}

function selectObjectCategory(category) {
    if (category === 'ip/domain') {
        object.value.template_uuid = '43b3b146-77eb-4931-b4cc-b66c60f28734';
        activeTemplate.value = objectsStore.getObjectTemplateByUuid('43b3b146-77eb-4931-b4cc-b66c60f28734');
    }
    document.getElementById('attributes-tab').click();

};

</script>

<style>
.tab-content {
    border-left: 1px solid #ddd;
    border-right: 1px solid #ddd;
    border-bottom: 1px solid #ddd;
    padding: 10px;
}

.nav-tabs {
    margin-bottom: 0;
}

.figure {
    width: 100px;
    text-align: center;
    vertical-align: middle;
}

button:hover .figure-caption {
    color: white;
}
</style>

<template>
    <div id="addObjectModal" class="modal fade" tabindex="-1" aria-labelledby="addObjectModalLabel" aria-hidden="true">
        <Form @submit="onSubmit" :validation-schema="ObjectSchema" v-slot="{ errors, isSubmitting }">
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="addObjectModalLabel">Add Object</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Discard"></button>
                    </div>
                    <div class="modal-body">
                        <ul class="nav nav-tabs" id="addObjectTabs" role="tablist">
                            <li class="nav-item" role="presentation">
                                <button class="nav-link active" id="category-tab" data-bs-toggle="tab"
                                    data-bs-target="#category" type="button" role="tab" aria-controls="category"
                                    aria-selected="true">Category</button>
                            </li>
                            <li class="nav-item" role="presentation">
                                <button class="nav-link" id="attributes-tab" data-bs-toggle="tab"
                                    data-bs-target="#attributes" type="button" role="tab" aria-controls="attributes"
                                    aria-selected="false">Attributes</button>
                            </li>
                            <!-- <li class="nav-item" role="presentation">
                                <button class="nav-link" id="distribution-tab" data-bs-toggle="tab"
                                    data-bs-target="#distribution" type="button" role="tab" aria-controls="distribution"
                                    aria-selected="false">Distribution</button>
                            </li> -->
                            <!-- <li class="nav-item" role="presentation">
                                <button class="nav-link" id="advanced-tab" data-bs-toggle="tab"
                                    data-bs-target="#advanced" type="button" role="tab" aria-controls="advanced"
                                    aria-selected="false">Advanced</button>
                            </li> -->
                            <li class="nav-item" role="presentation">
                                <button class="nav-link" id="preview-tab" data-bs-toggle="tab" data-bs-target="#preview"
                                    type="button" role="tab" aria-controls="preview"
                                    aria-selected="false">Preview</button>
                            </li>
                        </ul>
                        <div class="tab-content" id="add-object-tab-content">
                            <div class="tab-pane show active" id="category" role="tabpanel"
                                aria-labelledby="category-tab">
                                <button type="button" class="btn btn-outline-secondary m-1"
                                    @click="selectObjectCategory('ip/domain')">
                                    <figure class="figure m-1">
                                        <font-awesome-icon icon="fa-solid fa-network-wired" class="fa-2xl" />
                                        <figcaption class="figure-caption">Domain/IP</figcaption>
                                    </figure>
                                </button>
                                <button type="button" class="btn btn-outline-secondary m-1">
                                    <figure class="figure m-1">
                                        <font-awesome-icon icon="fa-solid fa-link" class="fa-2xl" />
                                        <figcaption class="figure-caption">URL/Domain</figcaption>
                                    </figure>
                                </button>
                                <button type="button" class="btn btn-outline-secondary m-1">
                                    <figure class="figure m-1">
                                        <font-awesome-icon icon="fa-solid fa-file-lines" class="fa-2xl" />
                                        <figcaption class="figure-caption">File/Hash</figcaption>
                                    </figure>
                                </button>
                                <button type="button" class="btn btn-outline-secondary m-1">
                                    <figure class="figure m-1">
                                        <font-awesome-icon icon="fa-solid fa-skull-crossbones" class="fa-2xl" />
                                        <figcaption class="figure-caption">Vulnerability</figcaption>
                                    </figure>
                                </button>
                                <button type="button" class="btn btn-outline-secondary m-1">
                                    <figure class="figure m-1">
                                        <font-awesome-icon icon="fa-solid fa-money-check-dollar" class="fa-2xl" />
                                        <figcaption class="figure-caption">Financial</figcaption>
                                    </figure>
                                </button>
                                <button type="button" class="btn btn-outline-secondary m-1">
                                    <figure class="figure m-1">
                                        <font-awesome-icon icon="fa-solid fa-person" class="fa-2xl" />
                                        <figcaption class="figure-caption">Personal</figcaption>
                                    </figure>
                                </button>
                                <div class="col text-start mt-3">
                                    <label for="object.template" class="form-label">Or select a template from the
                                        list:</label>
                                    <ObjectTemplateSelect name="object.template" :selected=object.template
                                        @object-template-updated="handleObjectTemplateUpdated"
                                        :errors="errors['object.template']" />
                                    <div class="invalid-feedback">{{ errors['object.template'] }}</div>
                                </div>
                            </div>
                            <div class="tab-pane" id="attributes" role="tabpanel" aria-labelledby="attributes-tab">
                                <AddObjectForm :object="object" :template="activeTemplate" />
                            </div>
                            <!-- <div class="tab-pane" id="distribution" role="tabpanel" aria-labelledby="distribution-tab">
                                distribution
                            </div> -->
                            <!-- <div class="tab-pane" id="advanced" role="tabpanel" aria-labelledby="advanced-tab">
                                <div class="row m-2">
                                    <div class="col col-6 text-start">
                                        <label for="object.distribution" class="form-label">distribution</label>
                                        <DistributionLevelSelect name="object.distribution"
                                            :selected=object.distribution
                                            @distribution-level-updated="handleDistributionLevelUpdated"
                                            :errors="errors['object.distribution']" />
                                        <div class="invalid-feedback">{{ errors['object.distribution'] }}</div>
                                    </div>
                                </div>
                                <div class="row m-2">
                                    <div class="col col-6 text-start">
                                        <label for="object.meta_category" class="form-label">meta-category</label>
                                        <ObjectMetaCategorySelect name="object.meta-category"
                                            :selected=object.meta_category
                                            @object-meta-category-updated="handleObjectMetaCategoryUpdated"
                                            :errors="errors['object.meta_category']" />
                                        <div class="invalid-feedback">{{ errors['object.meta_category'] }}</div>
                                    </div>
                                </div>
                                <div class="row m-2">
                                    <div class="col text-start">
                                        <label for="object.template" class="form-label">template</label>
                                        <ObjectTemplateSelect name="object.template" :selected=object.template
                                            @object-template-updated="handleObjectTemplateUpdated"
                                            :errors="errors['object.template']" />
                                        <div class="invalid-feedback">{{ errors['object.template'] }}</div>
                                    </div>
                                </div>
                            </div> -->
                            <div class="tab-pane" id="preview" role="tabpanel" aria-labelledby="preview-tab">
                                <AddObjectPreview :object="object" :template="activeTemplate"/>
                            </div>
                        </div>
                        <!-- TODO -->
                        <!--
                        <div class="row m-2">
                            <div class="col col-6 text-start">
                                <label for="objectSharingGroupId" class="form-label">Sharing Group</label>
                                <SharingGroupSelect v-model=object.sharing_group_id />
                                <div class="invalid-feedback">{{ errors['object.sharing_group_id'] }}</div>
                            </div>
                        </div> 
                        -->
                    </div>
                    <div v-if="errors.apiError" class="w-100 alert alert-danger mt-3 mb-3">
                        {{ errors.apiError }}
                    </div>
                    <div class="modal-footer">
                        <button id="closeModalButton" type="button" data-bs-dismiss="modal" class="btn btn-secondary"
                            @click="onClose()">Discard</button>
                        <button type="submit" class="btn btn-primary" :disabled="status.loading">
                            <span v-show="status.loading">
                                <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                            </span>
                            <span v-show="!status.loading">Add Object</span>
                        </button>
                    </div>
                </div>
            </div>
        </Form>
    </div>
</template>
