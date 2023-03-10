<script setup>

import { ref } from 'vue';
import { useObjectsStore } from "@/stores";
import { storeToRefs } from 'pinia'
import { ObjectSchema } from "@/schemas/object";
import { DISTRIBUTION_LEVEL } from "@/helpers/constants";
import DistributionLevelSelect from "@/components/enums/DistributionLevelSelect.vue";
import ObjectMetaCategorySelect from "@/components/enums/ObjectMetaCategorySelect.vue";
import ObjectTemplateSelect from "@/components/enums/ObjectTemplateSelect.vue";
import { Form, Field } from "vee-validate";
import * as Yup from "yup";

const objectsStore = useObjectsStore();
const { status } = storeToRefs(objectsStore);

const props = defineProps(['event_id']);
const emit = defineEmits(['object-created']);

const object = ref({
    distribution: DISTRIBUTION_LEVEL.INHERIT_EVENT,
    meta_category: "network",
    template_uuid: null,
    template: null
});

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

// function handleObjectMetaCategoryUpdated(metaCategory) {
//     object.value.meta_category = metaCategory;
// }

function handleObjectTemplateUpdated(templateUuid) {
    object.value.template_uuid = templateUuid;
    object.value.template = objectsStore.getObjectTemplateByUuid(templateUuid);
}

</script>

<template>
    <div id="addObjectModal" class="modal fade" tabindex="-1" aria-labelledby="addObjectModalLabel" aria-hidden="true">
        <Form @submit="onSubmit" :validation-schema="ObjectSchema" v-slot="{ errors, isSubmitting }">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="addObjectModalLabel">Add Object</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Discard"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row m-2">
                            <div class="col col-6 text-start">
                                <label for="object.distribution" class="form-label">distribution</label>
                                <DistributionLevelSelect name="object.distribution" :selected=object.distribution
                                    @distribution-level-updated="handleDistributionLevelUpdated"
                                    :errors="errors['object.distribution']" />
                                <div class="invalid-feedback">{{ errors['object.distribution'] }}</div>
                            </div>
                        </div>
                        <!-- <div class="row m-2">
                                                    <div class="col col-6 text-start">
                                                        <label for="object.meta_category" class="form-label">meta-category</label>
                                                        <ObjectMetaCategorySelect name="object.meta-category" :selected=object.meta_category
                                                            @object-meta-category-updated="handleObjectMetaCategoryUpdated"
                                                            :errors="errors['object.meta_category']" />
                                                        <div class="invalid-feedback">{{ errors['object.meta_category'] }}</div>
                                                    </div>
                                                </div> -->
                        <div class="row m-2">
                            <div class="col text-start">
                                <label for="object.template" class="form-label">template</label>
                                <ObjectTemplateSelect name="object.template" :selected=object.template
                                    @object-template-updated="handleObjectTemplateUpdated"
                                    :errors="errors['object.template']" />
                                <div class="invalid-feedback">{{ errors['object.template'] }}</div>
                            </div>
                        </div>
                        <!-- TODO -->
                        <!-- <div class="row m-2">
                                                        <div class="col col-6 text-start">
                                                            <label for="objectSharingGroupId" class="form-label">Sharing Group</label>
                                                            <SharingGroupSelect v-model=object.sharing_group_id />
                                                            <div class="invalid-feedback">{{ errors['object.sharing_group_id'] }}</div>
                                                        </div>
                                                    </div> -->
                    </div>
                    <div v-if="object.template">
                        {{ object.template }}
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
                            <span v-show="!status.loading">Add</span>
                        </button>
                    </div>
                </div>
            </div>
        </Form>
    </div>
</template>
