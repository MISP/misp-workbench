<script setup>
import { storeToRefs } from "pinia";
import Spinner from "@/components/misc/Spinner.vue";
import { useModulesStore } from "@/stores";

const modulesStore = useModulesStore();
const { modules, status } = storeToRefs(modulesStore);

modulesStore.getAll();

</script>
<template>
    <nav class="navbar">
        <div class="container-fluid">
            <a class="navbar-brand"></a>
            <form class="d-flex">
                <input class="form-control me-2" type="search" placeholder="Search" aria-label="Search">
                <button class="btn btn-outline-secondary" type="submit">Search</button>
            </form>
        </div>
    </nav>

    <Spinner v-if="status.loading" />
    <div v-if="status.error" class="text-danger">
        Error loading modules: {{ status.error }}
    </div>

    <div v-show="!status.loading">
        <div class="card mb-3" :key="module.name" v-for="module in modules">
            <h5 class="card-header">{{ module.name }} <span class="badge badge-pill bg-info"> v{{ module.meta.version
                    }}</span></h5>
            <div class="card-body">
                <p>
                <ul>
                    <li><span class="fw-bold">author/s:</span> {{ module.meta.author }}</li>
                    <li><span class="fw-bold">module type:</span> {{ module.meta.module_type }}</li>
                </ul>
                </p>
                <p class="card-text">{{ module.meta.description }}</p>
                <button type="button" class="btn btn-primary m-2">enable</button>
                <button type="button" class="btn btn-danger m-2">disable</button>
                <button type="button" class="btn btn-secondary m-2">configure</button>
            </div>
        </div>
    </div>
</template>