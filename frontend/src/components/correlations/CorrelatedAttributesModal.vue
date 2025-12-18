<script setup>
import { computed, ref, watch } from "vue";
import { router } from "@/router";

import Pagination from "@/components/misc/Pagination.vue";

const props = defineProps(["attribute", "modal"]);

// Pagination state
const page = ref(1);
const pageSize = ref(5);

const total = computed(() => (props.attribute?.correlations || []).length);
const totalPages = computed(() =>
  Math.max(1, Math.ceil(total.value / pageSize.value)),
);

// Reset page when attribute or pageSize changes
watch(
  () => [props.attribute && props.attribute.id, pageSize.value],
  () => {
    page.value = 1;
  },
);

const paginatedCorrelations = computed(() => {
  const list = props.attribute?.correlations || [];
  const start = (page.value - 1) * pageSize.value;
  return list.slice(start, start + pageSize.value);
});

function goToAttribute(id) {
  props.modal.hide();
  router.push(`/attributes/${id}`);
}

function goToEvent(id) {
  props.modal.hide();
  router.push(`/events/${id}`);
}

function handlePrevPage() {
  if (page.value > 1) page.value -= 1;
}

function handleNextPage() {
  if (page.value < totalPages.value) page.value += 1;
}

function handleSetPage(p) {
  const n = Number(p) || 1;
  page.value = Math.min(Math.max(1, n), totalPages.value);
}
</script>

<template>
  <div :id="`correlatedAttributesModal${attribute.id}`" class="modal">
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
              v-for="correlation in paginatedCorrelations"
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

        <div class="modal-footer d-flex flex-column">
          <div class="mt-3">
            <Pagination
              @nextPageClick="handleNextPage()"
              @prevPageClick="handlePrevPage()"
              @setPageClick="handleSetPage"
              :currentPage="page"
              :totalPages="totalPages"
              :hasPrevPage="page > 0"
              :hasNextPage="totalPages > 0"
            />
          </div>

          <div class="w-100 d-flex justify-content-end">
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
  </div>
</template>
