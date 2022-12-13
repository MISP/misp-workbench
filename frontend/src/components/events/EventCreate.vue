<script setup>
import DistributionLevelSelect from "@/components/enums/DistributionLevelSelect.vue";
import ThreatLevelSelect from "@/components/enums/ThreatLevelSelect.vue";
import AnalysisLevelSelect from "@/components/enums/AnalysisLevelSelect.vue";
import { Form, Field } from "vee-validate";
import { storeToRefs } from 'pinia'
import { useEventsStore } from "@/stores";
import { router } from "@/router";
import { EventSchema } from "@/schemas/event";

const eventsStore = useEventsStore();
const { status, error } = storeToRefs(eventsStore);

let event = {};

function onSubmit(values, { setErrors }) {
    return eventsStore
        .create(event)
        .then((response) => {
            router.push(`/events/${event.id}`);
        })
        .catch((error) => setErrors({ apiError: error }));
}

</script>

<template>
    <div class="card">
        <div class="card-header border-bottom">
            <div class="row">
                <div class="col-10">
                    <h3>Create Event</h3>
                </div>
            </div>
        </div>
        <div class="card-body d-flex flex-column">
            <Form @submit="onSubmit" :validation-schema="EventSchema" v-slot="{ errors, isSubmitting }">
                <div class="mb-3">
                    <label for="event.uuid">uuid</label>
                    <Field class="form-control" id="event.uuid" name="event.uuid" v-model="event.uuid"
                        :class="{ 'is-invalid': errors['event.uuid'] }">
                    </Field>
                    <div class=" invalid-feedback">{{ errors['event.uuid'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="event.info">info</label>
                    <Field class="form-control" id="event.info" name="event.info" v-model="event.info"
                        :class="{ 'is-invalid': errors['event.info'] }">
                    </Field>
                    <div class=" invalid-feedback">{{ errors['event.info'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="event.date">date</label>
                    <Field class="form-control" id="event.date" name="event.date" v-model="event.date"
                        :class="{ 'is-invalid': errors['event.date'] }">
                    </Field>
                    <div class=" invalid-feedback">{{ errors['event.date'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="event.distribution" class="form-label">distribution</label>
                    <DistributionLevelSelect name="event.distribution" v-model=event.distribution
                        :errors="errors['event.distribution']" />
                    <div class="invalid-feedback">{{ errors['event.distribution'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="event.threat_level" class="form-label">threat level</label>
                    <ThreatLevelSelect name="event.threat_level" v-model=event.threat_level
                        :errors="errors['event.threat_level']" />
                    <div class="invalid-feedback">{{ errors['event.threat_level'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="event.analysis" class="form-label">analysis</label>
                    <AnalysisLevelSelect name="event.analysis" v-model=event.analysis
                        :errors="errors['event.analysis']" />
                    <div class="invalid-feedback">{{ errors['event.analysis'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="event.extends_uuid">extends uuid</label>
                    <Field class="form-control" id="event.extends_uuid" name="event.extends_uuid"
                        v-model="event.extends_uuid" :class="{ 'is-invalid': errors['event.extends_uuid'] }">
                    </Field>
                    <div class=" invalid-feedback">{{ errors['event.extends_uuid'] }}</div>
                </div>
                <div v-if="error" class="w-100 alert alert-danger mt-3 mb-3">
                    {{ error }}
                </div>
                <button type="submit" class="btn btn-primary" :class="{ 'disabled': status.creating }">
                    <span v-if="status.creating">
                        <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                    </span>
                    <span v-if="!status.creating">Create</span>
                </button>
            </Form>
        </div>
    </div>
</template>