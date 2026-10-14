<script setup>
import { ref, computed } from "vue";
import { storeToRefs } from "pinia";
import { useEdlsStore, useAuthStore, useToastsStore } from "@/stores";
import { authHelper } from "@/helpers";
import { router } from "@/router";
import Spinner from "@/components/misc/Spinner.vue";
import Timestamp from "@/components/misc/Timestamp.vue";
import CopyToClipboard from "@/components/misc/CopyToClipboard.vue";
import EdlFormModal from "@/components/edls/EdlFormModal.vue";

const props = defineProps({ id: { type: [String, Number], required: true } });

const edlsStore = useEdlsStore();
const toastsStore = useToastsStore();
const { vendorsById } = storeToRefs(edlsStore);
const { scopes } = storeToRefs(useAuthStore());
const canManage = computed(() =>
  authHelper.hasScope(scopes.value, "edls:manage"),
);

const edl = ref(null);
const error = ref(null);
const preview = ref(null);
const tokens = ref([]);
const building = ref(false);

async function load() {
  try {
    edl.value = await edlsStore.get(props.id);
    preview.value = await edlsStore.preview(props.id);
    if (canManage.value) tokens.value = await edlsStore.tokens(props.id);
  } catch (err) {
    error.value = err;
  }
}
load();
edlsStore.getVendors().catch(() => {});

async function rebuild() {
  building.value = true;
  try {
    edl.value = await edlsStore.build(props.id);
    preview.value = await edlsStore.preview(props.id);
    if (edl.value.build_error) {
      toastsStore.push(`Build failed: ${edl.value.build_error}`, "danger");
    } else {
      toastsStore.push(
        `Rebuilt: ${edl.value.entry_count.toLocaleString()} entries.`,
        "success",
      );
    }
  } catch (err) {
    toastsStore.push(`${err}`, "danger");
  } finally {
    building.value = false;
  }
}

async function remove() {
  if (
    !confirm(
      `Delete "${edl.value.name}"? Firewalls fetching it get a 404 from now on.`,
    )
  )
    return;
  try {
    await edlsStore.remove(props.id);
    toastsStore.push(`"${edl.value.name}" deleted.`, "success");
    router.push("/edls");
  } catch (err) {
    toastsStore.push(`${err}`, "danger");
  }
}

function saved(updated) {
  edl.value = updated;
  toastsStore.push(`"${updated.name}" saved; it is being rebuilt.`, "success");
}

// Tokens
const draft = ref({ name: "", expires_at: "", allowed_ips: "" });
const creatingToken = ref(false);
const tokenError = ref(null);
// The token just created: its URL is shown this once.
const fresh = ref(null);

async function createToken() {
  tokenError.value = null;
  if (!draft.value.name.trim()) {
    tokenError.value = "Name the token (the firewall using it, say).";
    return;
  }
  creatingToken.value = true;
  try {
    const created = await edlsStore.createToken(props.id, {
      name: draft.value.name.trim(),
      expires_at: draft.value.expires_at
        ? new Date(`${draft.value.expires_at}T23:59:59`).toISOString()
        : null,
      allowed_ips: draft.value.allowed_ips
        .split(/[\s,]+/)
        .map((s) => s.trim())
        .filter(Boolean),
    });
    fresh.value = { ...created, url: edlsStore.urlOf(created.path) };
    draft.value = { name: "", expires_at: "", allowed_ips: "" };
    tokens.value = await edlsStore.tokens(props.id);
    edl.value = await edlsStore.get(props.id);
  } catch (err) {
    tokenError.value = `${err}`;
  } finally {
    creatingToken.value = false;
  }
}

async function revoke(token) {
  if (
    !confirm(
      `Revoke "${token.name}"? Firewalls using it get a 404 from now on.`,
    )
  )
    return;
  try {
    await edlsStore.revokeToken(props.id, token.id);
    if (fresh.value?.id === token.id) fresh.value = null;
    tokens.value = await edlsStore.tokens(props.id);
    edl.value = await edlsStore.get(props.id);
  } catch (err) {
    toastsStore.push(`${err}`, "danger");
  }
}

function tokenState(token) {
  if (token.revoked_at) return ["revoked", "text-bg-secondary"];
  if (token.expires_at && new Date(token.expires_at) <= new Date())
    return ["expired", "text-bg-secondary"];
  return ["active", "text-bg-success"];
}
</script>

<template>
  <div v-if="error" class="alert alert-danger">{{ error }}</div>
  <Spinner v-else-if="!edl" />
  <div v-else>
    <div class="card mb-3">
      <div
        class="card-header border-bottom d-flex justify-content-between align-items-center flex-wrap gap-2"
      >
        <h4 class="mb-0">
          {{ edl.name }}
          <span v-if="!edl.enabled" class="badge text-bg-secondary ms-2"
            >disabled</span
          >
        </h4>
        <div v-if="canManage" class="d-flex gap-2">
          <button
            type="button"
            class="btn btn-outline-secondary btn-sm"
            :disabled="building"
            @click="rebuild"
          >
            {{ building ? "Rebuilding…" : "Rebuild now" }}
          </button>
          <button
            type="button"
            class="btn btn-outline-primary btn-sm"
            data-bs-toggle="modal"
            data-bs-target="#edlEditModal"
          >
            Edit
          </button>
          <button
            type="button"
            class="btn btn-outline-danger btn-sm"
            @click="remove"
          >
            Delete
          </button>
        </div>
      </div>
      <div class="card-body">
        <p v-if="edl.description" class="text-muted">{{ edl.description }}</p>
        <dl class="row mb-0">
          <dt class="col-sm-3">Vendor</dt>
          <dd class="col-sm-9">
            {{ vendorsById[edl.vendor]?.name ?? edl.vendor }}
          </dd>
          <dt class="col-sm-3">Holds</dt>
          <dd class="col-sm-9">
            {{ edl.list_type }}
            <template v-if="edl.include_subdomains">, subdomains too</template>
            from
            <RouterLink :to="`/detection-profiles/update/${edl.profile_id}`"
              >its detection profile</RouterLink
            >
          </dd>
          <dt class="col-sm-3">Entries</dt>
          <dd class="col-sm-9">
            {{ edl.entry_count?.toLocaleString() ?? "–" }}
            <span v-if="edl.truncated" class="text-warning-emphasis">
              · {{ edl.truncated.toLocaleString() }} lower scored left out by
              the limit of
              {{
                (
                  edl.max_entries ?? vendorsById[edl.vendor]?.max_entries
                )?.toLocaleString()
              }}
            </span>
          </dd>
          <dt class="col-sm-3">Built</dt>
          <dd class="col-sm-9">
            <Timestamp v-if="edl.built_at" :timestamp="edl.built_at" />
            <span v-else class="text-muted">not yet</span>
            <span class="text-muted">
              · every {{ edl.refresh_minutes }} minutes</span
            >
            <div v-if="edl.build_error" class="text-danger small">
              The last build failed: {{ edl.build_error }}. The list built
              before it is still served.
            </div>
          </dd>
        </dl>
      </div>
    </div>

    <div v-if="canManage" class="card mb-3">
      <div class="card-header border-bottom">
        <h5 class="mb-0">Tokens</h5>
      </div>
      <div class="card-body">
        <p class="text-muted small">
          A token is in the URL, since firewalls can't send an Authorization
          header. Each one fetches this list and nothing else. Give each
          firewall its own, so you can revoke one without the others. Every
          fetch is audited.
        </p>
        <div v-if="fresh" class="alert alert-success" id="edl-fresh-token">
          <div class="fw-semibold mb-1">
            The URL for "{{ fresh.name }}", shown this once:
          </div>
          <div class="d-flex align-items-center">
            <code class="text-break flex-grow-1">{{ fresh.url }}</code>
            <CopyToClipboard :value="fresh.url" />
          </div>
          <div class="small mt-1">
            Only its hash is kept: copy it into the firewall's list settings
            now. If you lose it, revoke it and create another.
          </div>
        </div>
        <form class="row g-2 mb-3" @submit.prevent="createToken">
          <div class="col-md-3">
            <input
              v-model="draft.name"
              class="form-control"
              placeholder="fw-edge-01"
              aria-label="Token name"
            />
          </div>
          <div class="col-md-4">
            <input
              v-model="draft.allowed_ips"
              class="form-control font-monospace"
              placeholder="Only from: 192.0.2.10, 198.51.100.0/24"
              aria-label="Allowed addresses"
            />
          </div>
          <div class="col-md-3">
            <input
              v-model="draft.expires_at"
              type="date"
              class="form-control"
              aria-label="Expires"
              title="Expires at the end of this day (optional)"
            />
          </div>
          <div class="col-md-2">
            <button
              class="btn btn-primary w-100"
              type="submit"
              :disabled="creatingToken"
            >
              New token
            </button>
          </div>
          <div class="col-12 form-text mt-0">
            Addresses and expiry are optional: empty, the token works from
            anywhere until revoked.
          </div>
          <div v-if="tokenError" class="col-12 text-danger small">
            {{ tokenError }}
          </div>
        </form>
        <div class="table-responsive">
          <table class="table table-sm align-middle mb-0">
            <thead>
              <tr>
                <th>name</th>
                <th>token</th>
                <th>only from</th>
                <th>expires</th>
                <th>last used</th>
                <th class="text-end">uses</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="t in tokens" :key="t.id">
                <td>
                  {{ t.name }}
                  <span class="badge ms-1" :class="tokenState(t)[1]">{{
                    tokenState(t)[0]
                  }}</span>
                </td>
                <td class="font-monospace small">{{ t.prefix }}…</td>
                <td class="font-monospace small">
                  {{ t.allowed_ips.join(", ") || "anywhere" }}
                </td>
                <td class="small">
                  <Timestamp v-if="t.expires_at" :timestamp="t.expires_at" />
                  <span v-else class="text-muted">never</span>
                </td>
                <td class="small">
                  <template v-if="t.last_used_at">
                    <Timestamp :timestamp="t.last_used_at" />
                    <span class="text-muted font-monospace">
                      {{ t.last_used_ip }}</span
                    >
                  </template>
                  <span v-else class="text-muted">never</span>
                </td>
                <td class="text-end font-monospace">
                  {{ t.use_count.toLocaleString() }}
                </td>
                <td class="text-end">
                  <button
                    v-if="!t.revoked_at"
                    type="button"
                    class="btn btn-outline-danger btn-sm"
                    @click="revoke(t)"
                  >
                    Revoke
                  </button>
                </td>
              </tr>
              <tr v-if="!tokens.length">
                <td colspan="7" class="text-muted">
                  No token yet: nothing can fetch this list.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header border-bottom">
        <h5 class="mb-0">As served</h5>
      </div>
      <div class="card-body">
        <p v-if="preview?.lines.length" class="text-muted small">
          The first {{ preview.lines.length }} of
          {{ preview.entry_count.toLocaleString() }} entries, highest scored
          first.
        </p>
        <pre
          v-if="preview?.lines.length"
          class="bg-body-tertiary border rounded p-2 small mb-0"
          id="edl-preview"
          >{{ preview.lines.join("\n") }}</pre
        >
        <p v-else class="text-muted mb-0">
          {{ edl.built_at ? "The list is empty." : "Not built yet." }}
        </p>
      </div>
    </div>
    <EdlFormModal
      v-if="canManage"
      modal-id="edlEditModal"
      :edl="edl"
      @saved="saved"
    />
  </div>
</template>
