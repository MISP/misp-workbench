<script setup>
import { ref, computed } from "vue";
import { storeToRefs } from "pinia";
import {
  useLocalWarninglistsStore,
  useAuthStore,
  useToastsStore,
} from "@/stores";
import { authHelper } from "@/helpers";
import Timestamp from "@/components/misc/Timestamp.vue";

// Your organisation's own warninglists (every organisation's, for admins).
const listsStore = useLocalWarninglistsStore();
const toastsStore = useToastsStore();
const { lists, status } = storeToRefs(listsStore);
const { scopes } = storeToRefs(useAuthStore());
const canManage = computed(() =>
  authHelper.hasScope(scopes.value, "local_warninglists:manage"),
);

const creating = ref(false);
const draft = ref({ name: "", description: "" });

async function create() {
  if (!draft.value.name.trim()) return;
  try {
    await listsStore.create({
      name: draft.value.name.trim(),
      description: draft.value.description.trim() || null,
    });
    toastsStore.push(`"${draft.value.name}" created.`, "success");
    draft.value = { name: "", description: "" };
    creating.value = false;
    await listsStore.getAll();
  } catch (error) {
    toastsStore.push(`${error}`, "danger");
  }
}

listsStore.getAll();
</script>

<template>
  <div class="mb-4">
    <div class="d-flex justify-content-between align-items-center mb-2">
      <h5 class="mb-0">Your organisation's lists</h5>
      <button
        v-if="canManage"
        type="button"
        class="btn btn-outline-primary btn-sm"
        @click="creating = !creating"
      >
        + New list
      </button>
    </div>
    <p class="text-muted small mb-2">
      Values never to act on in your environment: your ranges and domains, VPN
      egress, partners, critical SaaS. The detection profiles attaching a list
      leave what it matches out. Only your organisation sees a list's entries
      and what it matches.
    </p>
    <form v-if="creating" class="row g-2 mb-3" @submit.prevent="create">
      <div class="col-12 col-md-4">
        <input
          v-model="draft.name"
          class="form-control"
          placeholder="Corporate ranges"
          aria-label="Name"
        />
      </div>
      <div class="col-12 col-md-6">
        <input
          v-model="draft.description"
          class="form-control"
          placeholder="What it holds, who owns it"
          aria-label="Description"
        />
      </div>
      <div class="col-12 col-md-2">
        <button class="btn btn-primary w-100" type="submit">Create</button>
      </div>
    </form>
    <div class="table-responsive">
      <table class="table table-sm align-middle mb-0">
        <thead>
          <tr>
            <th>name</th>
            <th class="text-end">entries</th>
            <th>source</th>
            <th class="text-end">enabled</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="list in lists" :key="list.id">
            <td>
              <RouterLink :to="`/settings/warninglists/local/${list.id}`">{{
                list.name
              }}</RouterLink>
              <div v-if="list.description" class="small text-muted">
                {{ list.description }}
              </div>
            </td>
            <td class="text-end font-monospace">
              {{ list.entry_count.toLocaleString() }}
            </td>
            <td class="small">
              <template v-if="list.source_url">
                synced
                <Timestamp v-if="list.synced_at" :timestamp="list.synced_at" />
                <template v-else>soon</template>
                <span
                  v-if="list.sync_error"
                  class="text-danger"
                  :title="list.sync_error"
                >
                  · failed</span
                >
              </template>
              <span v-else class="text-muted">by hand</span>
            </td>
            <td class="text-end">
              <span
                class="badge"
                :class="list.enabled ? 'text-bg-success' : 'text-bg-secondary'"
                >{{ list.enabled ? "on" : "off" }}</span
              >
            </td>
          </tr>
          <tr v-if="!lists.length && !status.loading">
            <td colspan="4" class="text-muted">
              No list yet.
              <template v-if="canManage"
                >Create one with "+ New list".</template
              >
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
