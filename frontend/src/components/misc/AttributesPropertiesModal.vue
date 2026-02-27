<script setup>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faFileCode } from "@fortawesome/free-solid-svg-icons";

const sample = {
  id: 42,
  uuid: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  event_id: 7,
  event_uuid: "3f5b1c7e-4a2d-4e8f-b6c1-9d0e2a3f5b1c",
  object_id: null,
  object_relation: null,
  category: "Network activity",
  type: "ip-dst",
  value: "192.168.1.100",
  to_ids: true,
  timestamp: 1700000000,
  "@timestamp": "2023-11-14T22:13:20",
  distribution: 0,
  sharing_group_id: null,
  comment: "",
  deleted: false,
  disable_correlation: false,
  first_seen: null,
  last_seen: null,
  data: "",
  tags: [{ name: "tlp:amber", colour: "#ffc000", exportable: true }],
  correlations: [],
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
    data-bs-target="#attributeDocSchemaModal"
  >
    open schema
    <FontAwesomeIcon :icon="faFileCode" class="ms-1" />
  </button>

  <Teleport to="body">
    <div
      class="modal fade"
      id="attributeDocSchemaModal"
      tabindex="-1"
      aria-hidden="true"
    >
      <div
        class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable"
      >
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Attribute document schema</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" />
          </div>

          <div class="modal-body">
            <p class="text-muted small mb-3">
              Each document in the <code>misp-attributes</code> index represents
              one MISP attribute. Use these fields in Lucene queries, e.g.
              <code>type:ip-dst AND to_ids:true</code>.
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
                  <td><code>uuid</code></td>
                  <td class="text-muted">keyword</td>
                  <td>Unique identifier of the attribute</td>
                </tr>
                <tr>
                  <td><code>event_uuid</code></td>
                  <td class="text-muted">keyword</td>
                  <td>UUID of the parent event</td>
                </tr>
                <tr>
                  <td><code>event_id</code></td>
                  <td class="text-muted">integer</td>
                  <td>Numeric ID of the parent event</td>
                </tr>
                <tr>
                  <td><code>type</code></td>
                  <td class="text-muted">keyword</td>
                  <td>MISP attribute type (e.g. ip-dst, domain, md5, url)</td>
                </tr>
                <tr>
                  <td><code>category</code></td>
                  <td class="text-muted">keyword</td>
                  <td>
                    Attribute category (e.g. Network activity, Payload delivery)
                  </td>
                </tr>
                <tr>
                  <td><code>value</code></td>
                  <td class="text-muted">text / keyword</td>
                  <td>The attribute value — full-text searchable</td>
                </tr>
                <tr>
                  <td><code>to_ids</code></td>
                  <td class="text-muted">boolean</td>
                  <td>Whether this attribute should be exported to IDS</td>
                </tr>
                <tr>
                  <td><code>@timestamp</code></td>
                  <td class="text-muted">date</td>
                  <td>
                    ISO 8601 datetime of when the attribute was last modified
                  </td>
                </tr>
                <tr>
                  <td><code>timestamp</code></td>
                  <td class="text-muted">integer</td>
                  <td>Unix epoch timestamp</td>
                </tr>
                <tr>
                  <td><code>distribution</code></td>
                  <td class="text-muted">integer</td>
                  <td>
                    Distribution level (0 = org only … 4 = all communities)
                  </td>
                </tr>
                <tr>
                  <td><code>comment</code></td>
                  <td class="text-muted">text</td>
                  <td>Free-text comment attached to the attribute</td>
                </tr>
                <tr>
                  <td><code>deleted</code></td>
                  <td class="text-muted">boolean</td>
                  <td>Soft-delete flag</td>
                </tr>
                <tr>
                  <td><code>disable_correlation</code></td>
                  <td class="text-muted">boolean</td>
                  <td>Whether correlation is disabled for this attribute</td>
                </tr>
                <tr>
                  <td><code>tags.name</code></td>
                  <td class="text-muted">keyword</td>
                  <td>
                    Tag names, e.g. <code>tags.name.keyword:"tlp:amber"</code>
                  </td>
                </tr>
                <tr>
                  <td><code>object_id</code> / <code>object_relation</code></td>
                  <td class="text-muted">integer / keyword</td>
                  <td>
                    Parent object ID and relation key (null if not in an object)
                  </td>
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
