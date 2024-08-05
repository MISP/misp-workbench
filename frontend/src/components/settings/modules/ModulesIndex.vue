<script setup>
import { ref, computed, nextTick } from "vue"
import { storeToRefs } from "pinia";
import Spinner from "@/components/misc/Spinner.vue";
import { useModulesStore } from "@/stores";
import ConfigureModuleModal from "@/components/settings/modules/ConfigureModuleModal.vue";
import QueryModuleModal from "@/components/settings/modules/QueryModuleModal.vue";
import { Modal } from 'bootstrap';

const modulesStore = useModulesStore();
const { modules, status } = storeToRefs(modulesStore);

modulesStore.getAll();

const searchTerm = ref('');

const showOnlyEnabled = ref(false);

const filteredModules = computed(() => {
    let tempFilteredModules = modules.value.filter(item =>
        item.name.toLowerCase().includes(searchTerm.value.toLowerCase())
    );

    if (showOnlyEnabled.value) {
        tempFilteredModules = tempFilteredModules.filter(item => item.enabled);
    }

    return tempFilteredModules;
});


function toggle(module_name) {
    modulesStore.toggle(module_name);
}

function dismissErrors() {
    modulesStore.dismissErrors();
}

const configureModuleModal = ref(null);
const queryModuleModal = ref(null);
const selectedModule = ref(null);

function showConfigureModuleModal() {
    configureModuleModal.value = new Modal(document.getElementById('configureModuleModal'));
    configureModuleModal.value.show();
}

function showQueryModuleModal() {
    queryModuleModal.value = new Modal(document.getElementById('queryModuleModal'));
    queryModuleModal.value.show();
}

function openConfigureModuleModal(module) {
    selectedModule.value = module;
    nextTick(() => {
        showConfigureModuleModal();
    });
}

function openQueryModuleModal(module) {
    selectedModule.value = module;
    nextTick(() => {
        showQueryModuleModal();
    });
}

function handleModuleConfigUpdate(event) {
    modules.value = modules.value.map(module => {
        if (module.name === event.module) {
            module.config = event.config;
        }
        return module;
    });
}
</script>

<template>
    <div class="container">
        <nav class="navbar">
            <div class="container-fluid">
                <a class="navbar-brand">misp-modules</a>
                <form class="d-flex" role="search">
                    <div class="input-group d-flex fs-5 mt-1">
                        <div class="form-check form-switch">
                            <input class="form-check-input" type="checkbox" v-model="showOnlyEnabled" role="switch"
                                id="showOnlyEnabledSwitch">
                            <label class="form-check-label" for="showOnlyEnabledSwitch">Only enabled</label>
                        </div>
                    </div>
                    <div class="input-group d-flex">
                        <span class="input-group-text"><font-awesome-icon icon="fa-solid fa-magnifying-glass" /></span>
                        <input type="text" class="form-control " v-model="searchTerm" placeholder="Search">
                    </div>
                </form>
            </div>
        </nav>

        <Spinner v-if="status.loading" />
        <div v-if="status.error" class="alert alert-danger alert-dismissible fade show" role="alert">
            <span>{{ status.error }} </span>
            <button type="button" class="btn-close" aria-label="Close" @click="dismissErrors()"></button>
        </div>

        <div v-show="!status.loading">
            <div class="card mb-3" :key="module.name" v-for="module in filteredModules">
                <h5 class="card-header">
                    {{ module.name }} <span class="badge badge-pill bg-info"> v{{
                                module.meta.version
                            }}</span>
                </h5>
                <div class="card-body">
                    <p>
                    <ul>
                        <li><span class="fw-bold">author/s:</span> {{ module.meta.author }}</li>
                        <li><span class="fw-bold">module type:</span> {{ module.meta.module_type }}</li>
                    </ul>
                    </p>
                    <p class="card-text">{{ module.meta.description }}</p>
                    <button v-if="module.enabled == false || !module.enabled" type="submit" class="btn btn-primary m-2"
                        :class="{ 'disabled': module.updating }" @click="toggle(module.name)">
                        <span v-if="module.updating">
                            <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                        </span>
                        <span v-if="!module.updating">enable</span>
                    </button>
                    <button v-if="module.enabled == true" type="submit" class="btn btn-danger m-2"
                        :class="{ 'disabled': module.updating }" @click="toggle(module.name)">
                        <span v-if="module.updating">
                            <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                        </span>
                        <span v-if="!module.updating">disable</span>
                    </button>
                    <button v-if="module.enabled" type="button" class="btn btn-success m-2"
                        @click="openQueryModuleModal(module)">query</button>
                    <button v-if="module.meta.config" type="button" class="btn btn-secondary  position-relative m-2"
                        @click="openConfigureModuleModal(module)">configure
                        <span v-if="module.config && Object.keys(module.config).length > 0"
                            class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-info">
                            {{ Object.keys(module.config).length }}
                            <span class="visually-hidden">custom settings</span>
                        </span></button>
                </div>
            </div>
        </div>
        <ConfigureModuleModal id="configureModuleModal" v-if="selectedModule" :modal="configureModuleModal"
            :module="selectedModule" @module-config-updated="handleModuleConfigUpdate" />
        <QueryModuleModal id="queryModuleModal" v-if="selectedModule" :key="selectedModule.name"
            :modal="queryModuleModal" :module="selectedModule" />
    </div>
</template>