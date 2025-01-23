<script setup>
import DistributionLevelSelect from "@/components/enums/DistributionLevelSelect.vue";
import ThreatLevelSelect from "@/components/enums/ThreatLevelSelect.vue";
import AnalysisLevelSelect from "@/components/enums/AnalysisLevelSelect.vue";
import Datepicker from "@/components/misc/Datepicker.vue";
import { Form, Field } from "vee-validate";
import { storeToRefs } from "pinia";
import { useEventsStore } from "@/stores";
import { router } from "@/router";
import { EventSchema } from "@/schemas/event";

const eventsStore = useEventsStore();
const { event, status, error } = storeToRefs(eventsStore);

function onSubmit(values, { setErrors }) {
  return eventsStore
    .update(values.event)
    .then((response) => {
      router.push(`/events/${values.event.id}`);
    })
    .catch((error) => setErrors({ apiError: error }));
}

function handleDistributionLevelUpdated(distributionLevelId) {
  event.distribution = parseInt(distributionLevelId);
}

function handleThreatLevelUpdated(threatLevelId) {
  event.threat_level = parseInt(threatLevelId);
}

function handleAnalysisLevelUpdated(analysisLevelId) {
  event.analysis = parseInt(analysisLevelId);
}
</script>

<template>
  <div class="card">
    <div class="card-header border-bottom">
      <div class="row">
        <div class="col-10">
          <h3>Update Event</h3>
        </div>
      </div>
    </div>
    <div class="card-body d-flex flex-column">
      <Form
        @submit="onSubmit"
        :validation-schema="EventSchema"
        v-slot="{ errors }"
      >
        <div class="mb-3">
          <label for="event.id">id</label>
          <Field
            class="form-control"
            id="event.id"
            name="event.id"
            v-model="event.id"
            :class="{ 'is-invalid': errors['event.id'] }"
            disabled
          >
          </Field>
          <div class="invalid-feedback">{{ errors["event.id"] }}</div>
        </div>
        <div class="mb-3">
          <label for="event.uuid">uuid</label>
          <Field
            class="form-control"
            id="event.uuid"
            name="event.uuid"
            v-model="event.uuid"
            :class="{ 'is-invalid': errors['event.uuid'] }"
            disabled
          >
          </Field>
          <div class="invalid-feedback">{{ errors["event.uuid"] }}</div>
        </div>
        <div class="mb-3">
          <label for="event.info">info</label>
          <Field
            class="form-control"
            id="event.info"
            name="event.info"
            v-model="event.info"
            :class="{ 'is-invalid': errors['event.info'] }"
          >
          </Field>
          <div class="invalid-feedback">{{ errors["event.info"] }}</div>
        </div>
        <div class="mb-3">
          <label for="event.date">date</label>
          <Datepicker v-model="event.date" name="event.date" />
        </div>
        <div class="mb-3">
          <label for="event.distribution" class="form-label"
            >distribution</label
          >
          <DistributionLevelSelect
            name="event.distribution"
            :selected="event.distribution"
            @distribution-level-updated="handleDistributionLevelUpdated"
            :errors="errors['event.distribution']"
          />
          <div class="invalid-feedback">{{ errors["event.distribution"] }}</div>
        </div>
        <div class="mb-3">
          <label for="event.threat_level" class="form-label"
            >threat level</label
          >
          <ThreatLevelSelect
            name="event.threat_level"
            :selected="event.threat_level"
            @threat-level-updated="handleThreatLevelUpdated"
            :errors="errors['event.threat_level']"
          />
          <div class="invalid-feedback">{{ errors["event.threat_level"] }}</div>
        </div>
        <div class="mb-3">
          <label for="event.analysis" class="form-label">analysis</label>
          <AnalysisLevelSelect
            name="event.analysis"
            :selected="event.analysis"
            @analysis-level-updated="handleAnalysisLevelUpdated"
            :errors="errors['event.analysis']"
          />
          <div class="invalid-feedback">{{ errors["event.analysis"] }}</div>
        </div>
        <div class="mb-3">
          <label for="event.extends_uuid">extends uuid</label>
          <Field
            class="form-control"
            id="event.extends_uuid"
            name="event.extends_uuid"
            v-model="event.extends_uuid"
            :class="{ 'is-invalid': errors['event.extends_uuid'] }"
          >
          </Field>
          <div class="invalid-feedback">{{ errors["event.extends_uuid"] }}</div>
        </div>
        <div class="mb-3">
          <label for="event.disable_correlation">disable correlation</label>
          <Field
            class="form-control"
            id="event.disable_correlation"
            name="event.disable_correlation"
            :value="event.push"
            v-model="event.disable_correlation"
            :class="{ 'is-invalid': errors['event.disable_correlation'] }"
          >
            <div class="form-check">
              <input
                class="form-check-input"
                type="checkbox"
                v-model="event.disable_correlation"
              />
            </div>
          </Field>
          <div class="invalid-feedback">
            {{ errors["attribute.disable_correlation"] }}
          </div>
        </div>
        <div v-if="errors.apiError" class="w-100 alert alert-danger mt-3 mb-3">
          {{ errors.apiError }}
        </div>
        <button
          type="submit"
          class="btn btn-outline-primary"
          :class="{ disabled: status.updating }"
        >
          <span v-if="status.updating">
            <span
              class="spinner-border spinner-border-sm"
              role="status"
              aria-hidden="true"
            ></span>
          </span>
          <span v-if="!status.updating">Save</span>
        </button>
      </Form>
    </div>
  </div>
</template>
