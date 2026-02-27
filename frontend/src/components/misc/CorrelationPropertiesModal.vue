<script setup>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faFileCode } from "@fortawesome/free-solid-svg-icons";

const sample = {
  source_event_uuid: "3f5b1c7e-4a2d-4e8f-b6c1-9d0e2a3f5b1c",
  source_attribute_uuid: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  target_event_uuid: "7c8d9e0f-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
  target_attribute_uuid: "f0e1d2c3-b4a5-9687-8796-a5b4c3d2e1f0",
  target_attribute_type: "ip-dst",
  target_attribute_value: "192.168.1.100",
  match_type: "term",
  score: 1.0,
};

const sampleJson = JSON.stringify(sample, null, 2);
</script>

<style scoped>
pre {
  background: var(--bs-body-bg);
  border: 1px solid var(--bs-border-color);
  border-radius: 0.375rem;
  padding: 1rem;
  font-size: 0.875rem;
  white-space: pre;
  overflow-x: auto;
}
</style>

<template>
  <button
    type="button"
    class="btn btn-sm btn-link p-0 text-decoration-none"
    data-bs-toggle="modal"
    data-bs-target="#correlationDocSchemaModal"
  >
    open schema
    <FontAwesomeIcon :icon="faFileCode" class="ms-1" />
  </button>

  <Teleport to="body">
    <div
      class="modal fade"
      id="correlationDocSchemaModal"
      tabindex="-1"
      aria-hidden="true"
    >
      <div class="modal-dialog modal-lg modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Correlation document schema</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" />
          </div>

          <div class="modal-body">
            <p class="text-muted small mb-3">
              Each document in the
              <code>misp-attribute-correlations</code> index has the following
              fields. Use them in Lucene queries, e.g.
              <code>match_type:term AND target_attribute_type:ip-dst</code>.
            </p>

            <div class="position-relative">
              <pre>{{ sampleJson }}</pre>
            </div>

            <table class="table table-sm table-bordered mt-3 mb-0 small">
              <thead class="table-light">
                <tr>
                  <th>Field</th>
                  <th>Type</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><code>source_event_uuid</code></td>
                  <td class="text-muted">keyword</td>
                  <td>UUID of the event containing the matched attribute</td>
                </tr>
                <tr>
                  <td><code>source_attribute_uuid</code></td>
                  <td class="text-muted">keyword</td>
                  <td>UUID of the matched attribute</td>
                </tr>
                <tr>
                  <td><code>target_event_uuid</code></td>
                  <td class="text-muted">keyword</td>
                  <td>UUID of the event being correlated against</td>
                </tr>
                <tr>
                  <td><code>target_attribute_uuid</code></td>
                  <td class="text-muted">keyword</td>
                  <td>UUID of the target attribute</td>
                </tr>
                <tr>
                  <td><code>target_attribute_type</code></td>
                  <td class="text-muted">keyword</td>
                  <td>MISP attribute type (e.g. ip-dst, domain, md5)</td>
                </tr>
                <tr>
                  <td><code>target_attribute_value</code></td>
                  <td class="text-muted">text / keyword</td>
                  <td>Value of the target attribute</td>
                </tr>
                <tr>
                  <td><code>match_type</code></td>
                  <td class="text-muted">keyword</td>
                  <td>
                    How the correlation was found:
                    <code>term</code>, <code>prefix</code>, <code>fuzzy</code>,
                    <code>cidr</code>
                  </td>
                </tr>
                <tr>
                  <td><code>score</code></td>
                  <td class="text-muted">float</td>
                  <td>Relevance score assigned by the correlation engine</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="modal-footer">
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
  </Teleport>
</template>
