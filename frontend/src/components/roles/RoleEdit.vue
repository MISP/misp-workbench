<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { storeToRefs } from "pinia";
import { useRolesStore } from "@/stores";
import { useRouter } from "vue-router";
import Spinner from "@/components/misc/Spinner.vue";
import RolesActions from "@/components/roles/RolesActions.vue";

const props = defineProps({ id: [String, Number] });

const router = useRouter();
const rolesStore = useRolesStore();
const { role, availableScopes, status } = storeToRefs(rolesStore);

const name = ref("");
const defaultRole = ref(false);
const selectedScopes = ref([]);
const apiError = ref(null);

onMounted(() => {
  rolesStore.getAvailableScopes();
  rolesStore.getById(props.id);
});

// Watch both role and availableScopes — expansion needs both to be loaded.
watch([role, availableScopes], ([r, scopes]) => {
  if (!r?.id || !Object.keys(scopes).length) return;
  name.value = r.name;
  defaultRole.value = r.default_role;
  selectedScopes.value = expandScopes(r.scopes, Object.keys(scopes));
});

function expandScopes(roleScopes, allScopes) {
  const result = new Set();
  for (const scope of roleScopes) {
    if (scope === "*") {
      allScopes.forEach((s) => result.add(s));
    } else if (scope.endsWith(":*")) {
      const prefix = scope.slice(0, -1); // "events:"
      allScopes
        .filter((s) => s.startsWith(prefix))
        .forEach((s) => result.add(s));
    } else {
      result.add(scope);
    }
  }
  return [...result];
}

const scopesByResource = computed(() => {
  const groups = {};
  for (const scope of Object.keys(availableScopes.value)) {
    const resource = scope.split(":")[0];
    if (!groups[resource]) groups[resource] = [];
    groups[resource].push(scope);
  }
  return groups;
});

function hasScope(scope) {
  return selectedScopes.value.includes(scope);
}

function toggleScope(scope) {
  const idx = selectedScopes.value.indexOf(scope);
  if (idx !== -1) {
    selectedScopes.value.splice(idx, 1);
  } else {
    selectedScopes.value.push(scope);
  }
}

function toggleResource(resource, scopeList) {
  const allSelected = scopeList.every((s) => hasScope(s));
  if (allSelected) {
    scopeList.forEach((s) => {
      const idx = selectedScopes.value.indexOf(s);
      if (idx !== -1) selectedScopes.value.splice(idx, 1);
    });
  } else {
    scopeList.forEach((s) => {
      if (!hasScope(s)) selectedScopes.value.push(s);
    });
  }
}

function isResourceFullySelected(scopeList) {
  return scopeList.every((s) => hasScope(s));
}

function onSubmit() {
  apiError.value = null;
  rolesStore
    .update(props.id, {
      name: name.value,
      default_role: defaultRole.value,
      scopes: selectedScopes.value,
    })
    .then(() => router.push(`/roles/${props.id}`))
    .catch((error) => (apiError.value = error));
}

function handleRoleDeleted() {
  router.push("/roles");
}
</script>

<template>
  <Spinner v-if="status.loading" />

  <form v-if="role?.id" @submit.prevent="onSubmit">
    <div class="card">
      <div
        class="card-header d-flex align-items-center justify-content-between"
      >
        <span class="fw-semibold">{{ role.name }}</span>
        <RolesActions
          :role_id="role.id"
          :role_name="role.name"
          :default_actions="{ view: true, update: false, delete: true }"
          @role-deleted="handleRoleDeleted"
        />
      </div>

      <div class="card-body row g-3">
        <div class="col-12 col-md-6">
          <label class="form-label fw-semibold">Name</label>
          <input v-model="name" type="text" class="form-control" required />
        </div>

        <div class="col-12 col-md-6 d-flex align-items-end">
          <div class="form-check">
            <input
              v-model="defaultRole"
              type="checkbox"
              class="form-check-input"
              id="defaultRoleCheck"
            />
            <label class="form-check-label" for="defaultRoleCheck">
              Default role
            </label>
          </div>
        </div>

        <div class="col-12">
          <label class="form-label fw-semibold">Scopes</label>
          <div class="row g-2">
            <div
              v-for="(scopeList, resource) in scopesByResource"
              :key="resource"
              class="col-12 col-md-6 col-xl-4"
            >
              <div class="border rounded p-2 h-100">
                <div class="form-check mb-1">
                  <input
                    type="checkbox"
                    class="form-check-input"
                    :id="`res_${resource}`"
                    :checked="isResourceFullySelected(scopeList)"
                    @change="toggleResource(resource, scopeList)"
                  />
                  <label
                    :for="`res_${resource}`"
                    class="form-check-label fw-semibold text-capitalize small"
                  >
                    {{ resource.replace(/_/g, " ") }}
                  </label>
                </div>
                <div
                  v-for="scope in scopeList"
                  :key="scope"
                  class="form-check ms-2"
                >
                  <input
                    type="checkbox"
                    class="form-check-input"
                    :id="`scope_${scope}`"
                    :checked="hasScope(scope)"
                    @change="toggleScope(scope)"
                  />
                  <label
                    :for="`scope_${scope}`"
                    class="form-check-label small font-monospace"
                  >
                    {{ scope }}
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="apiError" class="col-12">
          <div class="alert alert-danger">{{ apiError }}</div>
        </div>
      </div>

      <div class="card-footer d-flex gap-2">
        <button
          type="submit"
          class="btn btn-primary btn-sm"
          :class="{ disabled: status.updating }"
        >
          <span
            v-if="status.updating"
            class="spinner-border spinner-border-sm me-1"
          ></span>
          Save
        </button>
        <RouterLink
          :to="`/roles/${id}`"
          class="btn btn-outline-secondary btn-sm"
        >
          Cancel
        </RouterLink>
      </div>
    </div>
  </form>
</template>
