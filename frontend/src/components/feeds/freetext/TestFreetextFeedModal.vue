<script setup>
import { ref } from "vue";

const showRaw = ref(false);

defineProps({
  testResult: {
    type: Object,
    required: true,
  },
});

const emit = defineEmits(["closeModal"]);

const TYPE_BADGE = {
  "ip-src": "bg-danger",
  "ip-dst": "bg-danger",
  url: "bg-primary",
  domain: "bg-info text-dark",
  "email-src": "bg-warning text-dark",
  md5: "bg-secondary",
  sha1: "bg-secondary",
  sha256: "bg-secondary",
  sha512: "bg-secondary",
  cve: "bg-dark",
};

function typeBadgeClass(type) {
  return TYPE_BADGE[type] ?? "bg-secondary";
}

function closeModal() {
  emit("closeModal");
}
</script>

<style scoped>
.test-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1050;
}

.test-modal {
  width: 800px;
  max-width: 95%;
  max-height: 90vh;
  overflow-y: auto;
}
</style>

<template>
  <div class="test-modal-backdrop">
    <div class="test-modal">
      <div class="card">
        <div
          class="card-header d-flex justify-content-between align-items-center"
        >
          <strong>Freetext Feed Preview</strong>
          <button class="btn btn-sm btn-outline-secondary" @click="closeModal">
            ✕
          </button>
        </div>

        <div class="card-body">
          <div v-if="testResult?.success === false" class="alert alert-danger">
            {{ testResult.message || "Preview failed." }}
          </div>

          <div v-else-if="testResult?.rows?.length" class="table-responsive">
            <table class="table table-sm table-bordered mb-0">
              <thead class="table-secondary">
                <tr>
                  <th style="width: 30px">#</th>
                  <th>Value</th>
                  <th style="width: 140px">Type</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in testResult.rows" :key="idx">
                  <td>{{ idx + 1 }}</td>
                  <td>
                    <code class="small">{{ row.value }}</code>
                  </td>
                  <td>
                    <span class="badge" :class="typeBadgeClass(row.type)">
                      {{ row.type }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
            <small class="text-muted d-block mt-2">
              showing first {{ testResult.rows.length }} row{{
                testResult.rows.length !== 1 ? "s" : ""
              }}
            </small>
          </div>

          <div v-else class="text-muted text-center py-4">No rows parsed.</div>

          <hr />

          <div>
            <button
              class="btn btn-sm btn-outline-secondary mb-2"
              @click="showRaw = !showRaw"
            >
              {{ showRaw ? "Hide" : "Show" }} Raw JSON Results
            </button>
            <div v-if="showRaw">
              <pre class="p-3 rounded small overflow-auto">{{
                JSON.stringify(testResult, null, 2)
              }}</pre>
            </div>
          </div>
        </div>

        <div class="card-footer text-end">
          <button class="btn btn-secondary" @click="closeModal">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>
