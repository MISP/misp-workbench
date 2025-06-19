<script setup>
import { router } from "@/router";

const props = defineProps(["attribute", "modal"]);

function goToAttribute(id) {
  props.modal.hide();
  router.push(`/attributes/${id}`);
}

function goToEvent(id) {
  props.modal.hide();
  router.push(`/events/${id}`);
}
</script>

<template>
  <div :id="`attributeCorrelationsModal_${attribute.id}`" class="modal">
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">
            Attribute #{{ attribute.id }} Correlations
          </h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Discard"
          ></button>
        </div>
        <div class="modal-body">
          <div class="row g-3">
            <div
              v-for="correlation in attribute.correlations"
              :key="correlation._id"
              class="col-12"
            >
              <div class="card shadow-sm border-primary">
                <div class="card-body">
                  <ul class="list-group list-group-flush">
                    <li class="list-group-item">
                      <span class="badge bg-info text-dark me-2">{{
                        correlation._source.target_attribute_type
                      }}</span>
                      <a
                        href="#"
                        @click.prevent="
                          goToAttribute(
                            correlation._source.source_attribute_uuid,
                          )
                        "
                      >
                        {{ correlation._source.target_attribute_value }}
                      </a>
                    </li>
                    <li class="list-group-item">
                      <strong>Event: </strong>
                      <a
                        href="#"
                        @click.prevent="
                          goToEvent(correlation._source.target_event_uuid)
                        "
                      >
                        {{ correlation._source.target_event_uuid }}
                      </a>
                    </li>
                    <li class="list-group-item">
                      <strong>Match Type: </strong>
                      {{ correlation._source.match_type }}
                    </li>
                    <li class="list-group-item">
                      <strong>Score: </strong> {{ correlation._source.score }}
                    </li>
                    <li class="list-group-item">
                      <strong>Timestamp: </strong>
                      {{ correlation._source["@timestamp"] }}
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button
            id="closeModalButton"
            type="button"
            data-bs-dismiss="modal"
            class="btn btn-secondary"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
