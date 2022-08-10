<script setup>
import Sparkline from "@/components/charts/Sparkline.vue";
import AttributesIndex from "@/components/attributes/AttributesIndex.vue";
import ObjectsIndex from "@/components/objects/ObjectsIndex.vue";
import TagsIndex from "@/components/tags/TagsIndex.vue";
import DistributionLevel from "@/components/enums/DistributionLevel.vue";
import ThreatLevel from "@/components/enums/ThreatLevel.vue";
import AnalysisLevel from "@/components/enums/AnalysisLevel.vue";
import DistributionLevelSelect from "@/components/enums/DistributionLevelSelect.vue";
import ThreatLevelSelect from "@/components/enums/ThreatLevelSelect.vue";
import AnalysisLevelSelect from "@/components/enums/AnalysisLevelSelect.vue";

import { useEventsStore } from "@/stores";
const eventsStore = useEventsStore();

defineProps(['event', 'status']);
</script>

<template>
    <div class="card">
        <div class="card-header border-bottom">
            <div class="row">
                <div class="col-10">
                    <h3>Edit Event</h3>
                </div>
            </div>
        </div>
        <div class="card-body d-flex flex-column">
            <div class="mb-3">
                <label for="eventId" class="form-label">id</label>
                <input type=" text" id="eventId" v-model="event.id" class="form-control" placeholder="event id"
                    disabled>
            </div>
            <div class="mb-3">
                <label for="eventUuid" class="form-label">uuid</label>
                <input type=" text" id="eventUuid" v-model="event.uuid" class="form-control" placeholder="event uuid"
                    disabled>
            </div>
            <div class="mb-3">
                <label for="eventInfo" class="form-label">info</label>
                <input type=" text" id="eventInfo" v-model="event.info" class="form-control" placeholder="event info">
            </div>
            <div class="mb-3">
                <label for="eventDate" class="form-label">date</label>
                <input type="text" id="eventDate" v-model="event.date" class="form-control" placeholder="event date">
            </div>
            <div class="mb-3">
                <label for="eventDistribution" class="form-label">distribution</label>
                <DistributionLevelSelect v-model=event.distribution :selected=event.distribution />
            </div>
            <div class="mb-3">
                <label for="eventThreatLevel" class="form-label">threat level</label>
                <ThreatLevelSelect v-model=event.threat_level :selected=event.threat_level />
            </div>
            <div class="mb-3">
                <label for="eventAnalysisLevel" class="form-label">analysis</label>
                <AnalysisLevelSelect v-model=event.analysis :selected=event.analysis />
            </div>
            <div class="mb-3">
                <label for="eventExtendsUuid" class="form-label">extends</label>
                <input type=" text" id="eventExtendsUuid" v-model="event.extends_uuid" class="form-control">
            </div>
            <button type="submit" class="btn btn-primary" @click="eventsStore.update(event)"
                :class="{ 'disabled': status.updating }">

                <span v-if="status.updating">
                    <span class="sr-only">Saving...</span>
                    <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                </span>
                <span v-if="!status.updating">Save</span>
            </button>
        </div>
    </div>
</template>