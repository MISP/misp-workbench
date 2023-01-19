<script setup>
import { toRef } from 'vue';
import Sparkline from "@/components/charts/Sparkline.vue";
import AttributesIndex from "@/components/attributes/AttributesIndex.vue";
import ObjectsIndex from "@/components/objects/ObjectsIndex.vue";
import TagsIndex from "@/components/tags/TagsIndex.vue";
import DistributionLevel from "@/components/enums/DistributionLevel.vue";
import ThreatLevel from "@/components/enums/ThreatLevel.vue";
import AnalysisLevel from "@/components/enums/AnalysisLevel.vue";
import DeleteEventModal from "@/components/events/DeleteEventModal.vue";
import { router } from "@/router";

const props = defineProps(['event_id', 'event', 'status']);

function handleEventDeleted(event) {
    router.push(`/events`);
}
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
        <div class="event-title card-header border-bottom">
            <div class="row">
                <div class="col-10">
                    <h3>{{ event.info }}</h3>
                </div>
                <div class="col-2 text-end">
                    <div class="flex-wrap" :class="{ 'btn-group-vertical': $isMobile, 'btn-group': !$isMobile }"
                        aria-label="Event Actions">
                        <button type="button" class="btn btn-danger" data-bs-toggle="modal"
                            :data-bs-target="'#deleteEventModal-' + event.id">
                            <font-awesome-icon icon="fa-solid fa-trash" />
                        </button>
                        <RouterLink :to="`/events/update/${event.id}`" tag="button" class="btn btn-primary">
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
                                        <td>{{ event.id }}</td>
                                    </tr>
                                    <tr>
                                        <th>uuid</th>
                                        <td>{{ event.uuid }}
                                            <font-awesome-icon class="text-primary" icon="fa-solid fa-copy" />
                                        </td>
                                    </tr>
                                    <tr>
                                        <th>published</th>
                                        <td>{{ event.published }}</td>
                                    </tr>
                                    <tr>
                                        <th>creator user</th>
                                        <td>{{ event.user_id }}</td>
                                    </tr>
                                    <tr>
                                        <th>protected</th>
                                        <td>
                                            <div class="form-check form-switch">
                                                <input class="form-check-input" type="checkbox"
                                                    :checked="event.protected" disabled />
                                            </div>
                                        </td>
                                    </tr>
                                    <tr>
                                        <th>date</th>
                                        <td>{{ event.date }}</td>
                                    </tr>
                                    <tr>
                                        <th>threat level</th>
                                        <td>
                                            <ThreatLevel :threat_level_id=event.threat_level />
                                        </td>
                                    </tr>
                                    <tr>
                                        <th>analysis</th>
                                        <td>
                                            <AnalysisLevel :analysis_level_id=event.analysis />
                                        </td>
                                    </tr>
                                    <tr>
                                        <th>distribution</th>
                                        <td>
                                            <DistributionLevel :distribution_level_id=event.distribution />
                                        </td>
                                    </tr>
                                    <tr>
                                        <th>attributes</th>
                                        <td>{{ event.attribute_count }} ({{ event.object_count }} objects)</td>
                                    </tr>
                                    <tr>
                                        <th>disable correlation</th>
                                        <td>
                                            <div class="form-check form-switch">
                                                <input class="form-check-input" type="checkbox"
                                                    :checked="event.disable_correlation" disabled />
                                            </div>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col col-sm-3">
                <div class="mt-2">
                    <div class="card bg-light">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <p class="mb-0 text-muted">activity</p>
                                    <Sparkline :data="[2, 3, 5, 7, 18, 8, 6, 15, 23, 20, 21]" />
                                </div>
                            </div>
                        </div>
                        <div class="card-footer text-muted">
                            <p class="card-text fst-italic fw-light"><small class="text-muted">last day/week/<span
                                        class="fw-bold text-decoration-underline">month</span></small></p>
                        </div>
                    </div>
                </div>
                <div class="mt-2">
                    <div class="card bg-light">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <p class="mb-0 text-muted">correlations</p>
                                    <h2>8,523</h2>
                                </div>
                                <span class="badge badge-pill badge-cyan badge-red bg-warning fs-5">
                                    <font-awesome-icon icon="fa-solid fa-down-long" />
                                    <span class="font-weight-semibold ml-1">6.71%</span>
                                </span>
                            </div>

                        </div>
                        <div class="card-footer text-muted">
                            <p class="card-text fst-italic fw-light"><small class="text-muted ">last day/<span
                                        class="fw-bold text-decoration-underline">week</span>/month</small></p>
                        </div>
                    </div>
                </div>
                <div class="mt-2">
                    <div class="card">
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
            </div>
            <div class="col-xs-12 col-sm-12 col-md-12 col-lg-6 col-xl-3">
                <div class="mt-2">
                    <div class="card bg-light">
                        <div class="card-body d-flex flex-column">
                            <div class="card-text">
                                <img src="/public/images/pie-chart.png" class="card-img">
                            </div>
                        </div>
                    </div>
                </div>
                <div class="mt-2">
                    <div class="card h-100">
                        <div class="card-header">
                            <font-awesome-icon icon="fa-solid fa-tags" /> tags
                        </div>
                        <div class="card-body d-flex flex-column">
                            <div class="card-text">
                                <TagsIndex :tags="event.tags" />
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="row m-1">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <font-awesome-icon icon="fa-solid fa-shapes" /> objects
                    </div>
                    <div class="card-body d-flex flex-column">
                        <ObjectsIndex :event_id="event_id" :total_size="event.object_count" :page_size="10" />
                        <div class="mt-3">
                            <button type="button" class="w-100 btn btn-outline-primary">Add Object</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="row m-1">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <font-awesome-icon icon="fa-solid fa-cubes-stacked" /> attributes
                    </div>
                    <div class="card-body d-flex flex-column">
                        <AttributesIndex :event_id="event_id" :page_size="10" />
                    </div>
                </div>
            </div>

        </div>
        <div class="card-footer text-muted">
            <p class="card-text"><small class="text-muted">last updated 3 mins ago by <a
                        href="/users/123">adulau</a></small></p>
        </div>
        <DeleteEventModal @event-deleted="handleEventDeleted" :event_id="event.id" />
    </div>
</template>