<script setup>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faFileCode } from "@fortawesome/free-solid-svg-icons";

const sample = {
  id: 7,
  uuid: "3f5b1c7e-4a2d-4e8f-b6c1-9d0e2a3f5b1c",
  info: "Cobalt Strike C2 campaign targeting financial sector",
  date: "2023-11-14T00:00:00",
  published: true,
  analysis: 2,
  threat_level: 2,
  distribution: 3,
  sharing_group_id: null,
  attribute_count: 14,
  object_count: 2,
  org_id: 1,
  orgc_id: 1,
  user_id: 1,
  timestamp: 1700000000,
  "@timestamp": "2023-11-14T22:13:20",
  publish_timestamp: 1700001000,
  "@publish_timestamp": "2023-11-14T22:30:00",
  sighting_timestamp: null,
  locked: false,
  proposal_email_lock: false,
  disable_correlation: false,
  deleted: false,
  protected: null,
  extends_uuid: null,
  tags: [
    { name: "tlp:amber", colour: "#ffc000", exportable: true },
    {
      name: 'misp-galaxy:threat-actor="Cobalt Group"',
      colour: "#0088cc",
      exportable: true,
    },
  ],
  organisation: {
    id: 1,
    uuid: "5e4d3c2b-1a0f-9e8d-7c6b-5a4f3e2d1c0b",
    name: "ACME SOC",
    local: true,
    nationality: "US",
    sector: "Finance",
    type: null,
    description: null,
    contacts: null,
    landing_page: null,
    restricted_to_domain: null,
    created_by: 1,
    date_created: "2023-01-01T00:00:00",
    date_modified: "2023-01-01T00:00:00",
  },
  sharing_group: null,
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
    data-bs-target="#eventDocSchemaModal"
  >
    open schema
    <FontAwesomeIcon :icon="faFileCode" class="ms-1" />
  </button>

  <Teleport to="body">
    <div
      class="modal fade"
      id="eventDocSchemaModal"
      tabindex="-1"
      aria-hidden="true"
    >
      <div
        class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable"
      >
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Event document schema</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" />
          </div>

          <div class="modal-body">
            <p class="text-muted small mb-3">
              Each document in the <code>misp-events</code> index represents one
              MISP event (without its attributes or objects). Use these fields
              in Lucene queries, e.g.
              <code>threat_level:2 AND tags.name.keyword:"tlp:amber"</code>.
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
                  <td>Unique identifier of the event</td>
                </tr>
                <tr>
                  <td><code>info</code></td>
                  <td class="text-muted">text</td>
                  <td>Free-text event title — full-text searchable</td>
                </tr>
                <tr>
                  <td><code>date</code></td>
                  <td class="text-muted">date</td>
                  <td>Event date (ISO 8601)</td>
                </tr>
                <tr>
                  <td><code>@timestamp</code></td>
                  <td class="text-muted">date</td>
                  <td>ISO 8601 datetime of last modification</td>
                </tr>
                <tr>
                  <td><code>@publish_timestamp</code></td>
                  <td class="text-muted">date</td>
                  <td>
                    ISO 8601 datetime when the event was published (omitted if
                    unpublished)
                  </td>
                </tr>
                <tr>
                  <td><code>published</code></td>
                  <td class="text-muted">boolean</td>
                  <td>Whether the event has been published</td>
                </tr>
                <tr>
                  <td><code>threat_level</code></td>
                  <td class="text-muted">integer</td>
                  <td>1 = high, 2 = medium, 3 = low, 4 = undefined</td>
                </tr>
                <tr>
                  <td><code>analysis</code></td>
                  <td class="text-muted">integer</td>
                  <td>0 = initial, 1 = ongoing, 2 = completed</td>
                </tr>
                <tr>
                  <td><code>distribution</code></td>
                  <td class="text-muted">integer</td>
                  <td>0 = org only … 4 = all communities</td>
                </tr>
                <tr>
                  <td>
                    <code>attribute_count</code> / <code>object_count</code>
                  </td>
                  <td class="text-muted">integer</td>
                  <td>Number of attributes / objects in the event</td>
                </tr>
                <tr>
                  <td><code>disable_correlation</code></td>
                  <td class="text-muted">boolean</td>
                  <td>Whether correlation is disabled for this event</td>
                </tr>
                <tr>
                  <td><code>deleted</code></td>
                  <td class="text-muted">boolean</td>
                  <td>Soft-delete flag</td>
                </tr>
                <tr>
                  <td><code>tags.name</code></td>
                  <td class="text-muted">keyword</td>
                  <td>
                    Tag names, e.g. <code>tags.name.keyword:"tlp:red"</code>
                  </td>
                </tr>
                <tr>
                  <td><code>organisation.name</code></td>
                  <td class="text-muted">keyword</td>
                  <td>Reporting organisation name</td>
                </tr>
                <tr>
                  <td><code>organisation.uuid</code></td>
                  <td class="text-muted">keyword</td>
                  <td>Reporting organisation UUID</td>
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
