<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useModulesStore } from "@/stores";
import { storeToRefs } from 'pinia'

const modulesStore = useModulesStore();
const { status } = storeToRefs(modulesStore);

const props = defineProps(['module', 'modal']);
const emit = defineEmits(['module-config-updated']);

const settings = ref(props.module.meta.config)

const formData = reactive({});
const submittedData = ref(null);

onMounted(() => {
    settings.value.forEach(field => {
        formData[field] = props.module.config[field] || '';
    });
});


function configureModuleSettings() {
    submittedData.value = { ...formData };
    return modulesStore
        .configure(props.module.name, submittedData.value)
        .then((response) => {
            emit('module-config-updated', { "module": props.module.name, "config": submittedData.value });
            props.modal.hide();
        })
        .catch((error) => status.error = error);
}

function clearModuleSettings() {
    submittedData.value = { ...formData };
    return modulesStore
        .configure(props.module.name, {})
        .then((response) => {
            emit('module-config-updated', { "module": props.module.name, "config": {} });
            props.modal.hide();
        })
        .catch((error) => status.error = error);
}
</script>

<template>
    <div v-if="module" id="configureModuleModal" class="modal" aria-labelledby="configureModuleModal"
        aria-hidden="true">
        <div class="modal-dialog modal-lg">
            <div v-if="module" class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">{{ module.name }}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Discard"></button>
                </div>
                <div class="modal-body">
                    <div v-for="setting in settings">
                        <form class="row align-items-center">
                            <div class="col">
                                <label :for="setting" class="col-form-label">{{ setting }}</label>
                            </div>
                            <div class="col">
                                <input class="form-control" :id="setting" v-model="formData[setting]">
                            </div>
                        </form>
                    </div>

                </div>
                <div v-if="status.error" class="w-100 alert alert-danger mt-3 mb-3">
                    {{ status.error }}
                </div>
                <div class="modal-footer">
                    <button id="closeModalButton" type="button" data-bs-dismiss="modal"
                        class="btn btn-outline-secondary">Discard</button>
                    <button type="submit" @click="clearModuleSettings" class="btn btn-outline-primary"
                        :class="{ 'disabled': status.loading }">
                        <span v-if="status.loading">
                            <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                        </span>
                        <span v-if="!status.loading">Clear</span>
                    </button>
                    <button type="submit" @click="configureModuleSettings" class="btn btn-primary"
                        :class="{ 'disabled': status.loading }">
                        <span v-if="status.loading">
                            <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                        </span>
                        <span v-if="!status.loading">Save</span>
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>
