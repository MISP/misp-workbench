<script setup>
import { ref, computed } from "vue";
import CopyToClipboard from "@/components/misc/CopyToClipboard.vue";

const categories = [
  "All",
  "IDs",
  "Strings",
  "Tags",
  "Geolocation",
  "Time",
  "Boolean",
  "Scoring",
  "Misc",
];

const examples = [
  {
    category: "IDs",
    title: "Match by UUID",
    query: 'uuid:"094cecb9-2bd0-4c15-97f1-21373601b364"',
    description: "Exact match on a document UUID.",
  },
  {
    category: "Strings",
    title: "Wildcard prefix",
    query: "type.keyword:ip*",
    description: "Matches ip, ip-src, ip-dst, etc.",
  },
  {
    category: "Tags",
    title: "TLP filtering",
    query: 'tags.name.keyword:"tlp:amber"',
    description: "Exact match on TLP amber tags.",
  },
  {
    category: "Geolocation",
    title: "Country filter",
    query: 'expanded.ip2geo.country_iso_code:"RU"',
    description: "Attributes geolocated to Russia.",
  },
  {
    category: "Time",
    title: "Date range",
    query: "@timestamp:[2023-01-01 TO *]",
    description: "Everything from Jan 2023 until now.",
  },
  {
    category: "Boolean",
    title: "IP attributes excluding TLP white",
    query: 'type:ip-src AND NOT tags.name:"tlp:white"',
    description: "Useful for actionable IPs only.",
  },
  {
    category: "Scoring",
    title: "Boost IP source attributes",
    query: "type:ip-src^2 tags.name:tlp:red",
    description: "Prioritize IP sources with red TLP.",
  },
  {
    category: "Misc",
    title: "C2 keyword search",
    query: "value:*c2*",
    description: "Substring match inside attribute values.",
  },
];

const selectedCategory = ref("All");

const filteredExamples = computed(() => {
  if (selectedCategory.value === "All") return examples;
  return examples.filter((e) => e.category === selectedCategory.value);
});
</script>

<style>
.modal {
  z-index: 10;
}
.lucene-modal-body {
  height: 65vh;
  display: flex;
  flex-direction: column;
  padding-bottom: 0;
}

.lucene-filters {
  position: sticky;
  top: 0;
  z-index: 2;
  border-bottom: 1px solid var(--bs-border-color);
}

.lucene-results {
  overflow-y: auto;
  overflow-x: hidden;
  padding-bottom: 1rem;
}

.lucene-filters {
  box-shadow: 0 4px 6px -6px rgba(0, 0, 0, 0.25);
}
.lucene-results code {
  background: var(--bs-body-bg);
  padding: 0.25rem 0.4rem;
  border-radius: 0.25rem;
  font-size: 0.85rem;
}

.lucene-results .card-body {
  overflow-x: hidden;
}
</style>

<template>
  <div
    class="modal fade"
    id="luceneQuerySyntaxCheatsheetModal"
    tabindex="-1"
    aria-hidden="true"
  >
    <div
      class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable"
    >
      <div class="modal-content">
        <div class="modal-header">
          <h1 class="modal-title fs-5">Lucene Query Syntax Cheatsheet</h1>
          <button type="button" class="btn-close" data-bs-dismiss="modal" />
        </div>
        <div class="modal-body lucene-modal-body">
          <div class="lucene-filters sticky-top bg-body pb-2 mb-3">
            <div class="d-flex flex-wrap gap-2">
              <button
                v-for="cat in categories"
                :key="cat"
                class="btn btn-sm"
                :class="
                  cat === selectedCategory
                    ? 'btn-primary'
                    : 'btn-outline-secondary'
                "
                @click="selectedCategory = cat"
              >
                {{ cat }}
              </button>
            </div>
          </div>
          <div class="lucene-results">
            <div class="row g-3 transition-opacity">
              <div
                v-for="ex in filteredExamples"
                :key="ex.title"
                class="col-12 col-md-6"
              >
                <div class="card h-100">
                  <div class="card-header bg-body-secondary">
                    <span class="fw-semibold">{{ ex.title }}</span>
                  </div>

                  <div class="card-body">
                    <code>{{ ex.query }}</code>
                    <CopyToClipboard :value="ex.query" />

                    <p class="small text-muted mb-0">
                      {{ ex.description }}
                    </p>
                  </div>

                  <div class="card-footer text-muted small">
                    Category: {{ ex.category }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <span class="text-muted small me-auto">
            <strong>Tip:</strong> Click queries to copy & paste into Explore
          </span>
          <button
            type="button"
            class="btn btn-secondary"
            data-bs-dismiss="modal"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
