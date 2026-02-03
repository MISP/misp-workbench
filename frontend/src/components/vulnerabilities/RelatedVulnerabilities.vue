<script setup>
import { onMounted } from "vue";
import { storeToRefs } from "pinia";
import { useEventsStore } from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
const props = defineProps({
  event_uuid: {
    type: String,
    required: true,
  },
});

const eventsStore = useEventsStore();
const { vulnerabilities, status } = storeToRefs(eventsStore);

onMounted(() => {
  eventsStore.getVulnerabilities(props.event_uuid);
});

function severityClass(severity) {
  switch (severity) {
    case "CRITICAL":
      return "bg-danger";
    case "HIGH":
      return "bg-warning text-dark";
    case "MEDIUM":
      return "bg-info";
    case "LOW":
      return "bg-secondary";
    default:
      return "bg-light text-dark";
  }
}
</script>

<template>
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
      <span>Vulnerabilities</span>
      <span v-if="vulnerabilities.length" class="badge bg-secondary">
        {{ vulnerabilities.length }}
      </span>
    </div>

    <div class="card-body p-0">
      <div v-if="status === 'loading'" class="p-3 text-center text-muted">
        <FontAwesomeIcon icon="spinner" spin /> Loading...
      </div>

      <div v-else-if="status === 'error'" class="p-3 text-danger">
        Error loading vulnerabilities.
      </div>

      <div v-else-if="vulnerabilities.length" class="accordion accordion-flush">
        <div
          v-for="(vuln, index) in vulnerabilities"
          :key="vuln.attribute_uuid"
          class="accordion-item"
        >
          <h2 class="accordion-header">
            <button
              class="accordion-button collapsed d-flex gap-2"
              type="button"
              data-bs-toggle="collapse"
              :data-bs-target="`#vuln-${index}`"
            >
              <span class="fw-bold">{{ vuln.vuln_id }}</span>

              <span class="badge ms-auto" :class="severityClass(vuln.severity)">
                {{ vuln.severity }}
              </span>
            </button>
          </h2>

          <div :id="`vuln-${index}`" class="accordion-collapse collapse">
            <div class="accordion-body">
              <p class="mb-3 text-muted">
                {{ vuln.description }}
              </p>
              <div v-if="vuln.detection_rules?.length" class="mt-3">
                <strong>Detection rules</strong>
                <br />
                <ul class="mb-0 ps-3">
                  <li v-for="(rule, idx) in vuln.detection_rules" :key="idx">
                    <span
                      class="d-inline-flex align-items-center ms-2"
                      style="max-width: 100%"
                    >
                      <span class="badge bg-secondary me-2">{{
                        rule.format
                      }}</span>
                      <span
                        class="text-truncate"
                        :title="rule.title"
                        style="
                          display: inline-block;
                          max-width: 60%;
                          white-space: nowrap;
                          overflow: hidden;
                          text-overflow: ellipsis;
                        "
                      >
                        {{ rule.title }}
                      </span>
                      <span
                        ><a
                          :href="`https://rulezet.org/rule/detail_rule/${rule.id}`"
                          target="_blank"
                          rel="noopener"
                        >
                          <FontAwesomeIcon :icon="faExternalLinkAlt" /> </a
                      ></span>
                    </span>
                  </li>
                </ul>
              </div>

              <div v-if="vuln.impacted_products?.length" class="mt-3">
                <strong>Impacted products</strong>
                <ul class="mb-0 ps-3">
                  <li
                    v-for="(product, idx) in vuln.impacted_products"
                    :key="idx"
                  >
                    {{ product.vendor }} / {{ product.product }}
                    <span
                      v-for="(v, i) in product.versions"
                      :key="i"
                      class="text-muted"
                    >
                      — {{ v.version }}
                    </span>
                  </li>
                </ul>
              </div>

              <div v-if="vuln.references?.length" class="mt-3">
                <strong>References</strong>
                <ul class="mb-0 ps-3">
                  <li v-for="(ref, idx) in vuln.references" :key="idx">
                    <a :href="ref" target="_blank" rel="noopener">
                      {{ ref }}
                    </a>
                  </li>
                </ul>
              </div>

              <div class="mt-3">
                <strong>More Information</strong>
                <br />
                <span>
                  <a
                    :href="`https://vulnerability.circl.lu/vuln/${vuln.vuln_id}`"
                    target="_blank"
                    rel="noopener"
                  >
                    {{ `https://vulnerability.circl.lu/vuln/${vuln.vuln_id}` }}
                  </a>
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="alert alert-secondary m-3" role="alert">
        No related vulnerabilities found.
      </div>
    </div>
  </div>
</template>
