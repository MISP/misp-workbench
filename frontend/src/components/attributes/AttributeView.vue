<script setup>
import Sparkline from "@/components/charts/Sparkline.vue";
import TagsIndex from "@/components/tags/TagsIndex.vue";
import DistributionLevel from "@/components/enums/DistributionLevel.vue";
import ThreatLevel from "@/components/enums/ThreatLevel.vue";
import AnalysisLevel from "@/components/enums/AnalysisLevel.vue";

const props = defineProps(['attribute', 'status']);
</script>

<style>
.single-stat-card .card-body {
    font-size: x-large;
    text-align: center;
    padding: 0;
}

div.row h3 {
    margin-bottom: 0;
}

.single-stat-card .card-body p {
    margin-bottom: 0;
}
</style>
<template>
    <div class="card">
        <div class="attribute-title card-header border-bottom">
            <div class="row">
                <div class="col-10">
                </div>
                <div class="col-2 text-end">
                    <div class="flex-wrap" :class="{ 'btn-group-vertical': $isMobile, 'btn-group': !$isMobile }"
                        aria-label="Attribute Actions">
                        <RouterLink :to="`/attributes/delete/${attribute.id}`" tag="button"
                            class="btn btn-danger disabled">
                            <font-awesome-icon icon="fa-solid fa-trash" />
                        </RouterLink>
                        <RouterLink :to="`/attributes/update/${attribute.id}`" tag="button" class="btn btn-primary">
                            <font-awesome-icon icon="fa-solid fa-pen" />
                        </RouterLink>
                    </div>
                </div>
            </div>
        </div>
        <div class="row m-1">
            <div class="col-sm-6 mt-2">
                <div class="card">
                    <div class="card-body d-flex flex-column">
                        <div class="table-responsive-sm">
                            <table class="table table-striped">
                                <tbody>
                                    <tr>
                                        <th>id</th>
                                        <td>{{ attribute.id }}</td>
                                    </tr>
                                    <tr>
                                        <th>uuid</th>
                                        <td>{{ attribute.uuid }}
                                            <font-awesome-icon class="text-primary" icon="fa-solid fa-copy" />
                                        </td>
                                    </tr>
                                    <tr>
                                        <th>timestamp</th>
                                        <td>{{ attribute.timestamp }}</td>
                                    </tr>
                                    <tr>
                                        <th>analysis</th>
                                        <td>
                                            <AnalysisLevel :analysis_level_id=attribute.analysis />
                                        </td>
                                    </tr>
                                    <tr>
                                        <th>distribution</th>
                                        <td>
                                            <DistributionLevel :distribution_level_id=attribute.distribution />
                                        </td>
                                    </tr>
                                    <tr>
                                        <th>correlation</th>
                                        <td>
                                            <div class="form-check form-switch">
                                                <input class="form-check-input" type="checkbox"
                                                    :checked="!attribute.disable_correlation" disabled />
                                            </div>
                                        </td>
                                    </tr>
                                    <tr>
                                        <th>category</th>
                                        <td>{{ attribute.category }}</td>
                                    </tr>
                                    <tr>
                                        <th>type</th>
                                        <td>{{ attribute.type }}</td>
                                    </tr>
                                    <tr>
                                        <th>value</th>
                                        <td>{{ attribute.value }}</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-xs-12 col-sm-12 col-md-12 col-lg-6 col-xl-3">
                <div class="mt-2 card bg-light">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <p class="mb-0 text-muted">activity</p>
                                <Sparkline v-bind:data="[2, 3, 5, 7, 18, 8, 6, 15, 23, 20, 21]" />
                            </div>
                        </div>
                    </div>
                    <div class="card-footer text-muted">
                        <p class="card-text fst-italic fw-light"><small class="text-muted">last day/week/<span
                                    class="fw-bold text-decoration-underline">month</span></small></p>
                    </div>
                </div>
                <div class="mt-2 card">
                    <div class="card-body bg-light">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <p class="mb-0 text-muted">sightings</p>
                                <h2>423</h2>
                            </div>
                            <span class="badge badge-pill badge-cyan badge-red bg-danger fs-5">
                                <font-awesome-icon icon="fa-solid fa-up-long" />
                                <span class="font-weight-semibold ml-1">16.71%</span>
                            </span>
                        </div>
                    </div>
                    <div class="card-footer text-muted">
                        <p class="card-text fst-italic fw-light"><small class="text-muted">last day/week/<span
                                    class="fw-bold text-decoration-underline">month</span></small></p>
                    </div>
                </div>
            </div>
            <div class="col col-sm-3">
                <div class="card mt-2">
                    <div class="card-header">
                        <font-awesome-icon icon="fa-solid fa-tags" /> tags
                    </div>
                    <div class="card-body d-flex flex-column">
                        <div class="card-text">
                            <TagsIndex :tags="attribute.tags" />
                        </div>
                    </div>
                </div>
            </div>

        </div>
    </div>
</template>