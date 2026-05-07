<script setup>
import { faBook, faCopy } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useToastsStore } from "@/stores";

defineProps({
  modalId: { type: String, default: "mwctipyDocsModal" },
});

const toastsStore = useToastsStore();

const SECTIONS = [
  {
    title: "Reads",
    rows: [
      {
        signature: "mwlab.get_event(event_uuid: str)",
        snippet: 'mwlab.get_event("ba4b11b6-dcce-4315-8fd0-67b69160ea76")',
        description: "Look up an event by uuid. Returns dict | None.",
      },
      {
        signature: "mwlab.get_attribute(attribute_uuid: str)",
        snippet: 'mwlab.get_attribute("8c9f...")',
        description: "Look up an attribute by uuid.",
      },
      {
        signature: "mwlab.get_object(object_uuid: str)",
        snippet: 'mwlab.get_object("...")',
        description: "Look up a MISP object by uuid.",
      },
    ],
  },
  {
    title: "Search",
    rows: [
      {
        signature: "mwlab.search_events(query=None, tags=None, size=50)",
        snippet:
          'mwlab.search_events(query="ransomware", tags=["tlp:white"], size=20)',
        description:
          "Free-text query over event.info plus an AND-list of tag names.",
      },
      {
        signature: "mwlab.search_attributes(value=None, type=None, size=50)",
        snippet: 'mwlab.search_attributes(value="8.8.8.8", type="ip-src")',
        description: "Match value substring + optional attribute type.",
      },
    ],
  },
  {
    title: "Modules / enrichment",
    rows: [
      {
        signature: "mwlab.modules(enabled_only=True)",
        snippet: "mwlab.modules()",
        description: "List MISP expansion modules. Doesn't hit external APIs.",
      },
      {
        signature: "mwlab.enrich(value, type, module, config=None)",
        snippet: 'mwlab.enrich("8.8.8.8", "ip-src", "mmdb_lookup")',
        description:
          "Run an expansion module. Audited under actor_type=lab_notebook.",
      },
    ],
  },
  {
    title: "Convenience",
    rows: [
      {
        signature: "mwlab.dataframe(rows: list[dict])",
        snippet:
          'rows = mwlab.search_events(tags=["tlp:white"], size=10)\nmwlab.dataframe(rows)',
        description:
          "Wrap rows in a pandas.DataFrame. End the cell with the call to render as text/html.",
      },
    ],
  },
  {
    title: "render.* (HTML helpers)",
    rows: [
      {
        signature: "render.timeline(events)",
        snippet:
          "from IPython.display import HTML\nHTML(render.timeline(mwlab.search_events(size=20)))",
        description: "Most-recent-first event list as a sized HTML <ul>.",
      },
      {
        signature: "render.tag_cloud(rows)",
        snippet:
          "from IPython.display import HTML\nHTML(render.tag_cloud(mwlab.search_attributes(size=200)))",
        description:
          "Tag-frequency cloud sized by count across the supplied rows.",
      },
    ],
  },
];

async function copy(snippet) {
  try {
    await navigator.clipboard.writeText(snippet);
    toastsStore.push("Snippet copied to clipboard.", "success");
  } catch {
    toastsStore.push("Couldn't copy — check clipboard permissions.", "warning");
  }
}
</script>

<template>
  <div
    class="modal fade"
    :id="modalId"
    tabindex="-1"
    :aria-labelledby="`${modalId}Label`"
    aria-hidden="true"
  >
    <div class="modal-dialog modal-xl modal-dialog-scrollable">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" :id="`${modalId}Label`">
            <FontAwesomeIcon :icon="faBook" class="me-2" />
            mwctipy reference
          </h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Close"
          ></button>
        </div>
        <div class="modal-body small">
          <p class="text-muted">
            <code>mwlab</code> is bound at kernel startup with your user id and
            the current notebook id; every call is audited under
            <code>actor_type=lab_notebook</code>. <code>render.*</code> returns
            raw HTML strings — wrap with
            <code>IPython.display.HTML(...)</code> to render in a cell.
          </p>
          <template v-for="section in SECTIONS" :key="section.title">
            <h6 class="mt-3">{{ section.title }}</h6>
            <table class="table table-sm align-middle">
              <thead>
                <tr>
                  <th style="width: 35%">Signature</th>
                  <th>Description</th>
                  <th style="width: 80px"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in section.rows" :key="row.signature">
                  <td>
                    <code>{{ row.signature }}</code>
                  </td>
                  <td>{{ row.description }}</td>
                  <td class="text-end">
                    <button
                      class="btn btn-outline-secondary btn-sm"
                      title="Copy snippet"
                      @click="copy(row.snippet)"
                    >
                      <FontAwesomeIcon :icon="faCopy" />
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </template>
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
</template>
