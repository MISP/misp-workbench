<script setup>
import { computed, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { useRolesStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import RolesActions from "@/components/roles/RolesActions.vue";
import { useRouter } from "vue-router";

const props = defineProps({ id: [String, Number] });

const router = useRouter();
const rolesStore = useRolesStore();
const { role, status } = storeToRefs(rolesStore);

onMounted(() => rolesStore.getById(props.id));

const scopesByResource = computed(() => {
  if (!role.value?.scopes) return {};
  const groups = {};
  for (const scope of role.value.scopes) {
    const resource = scope.split(":")[0];
    if (!groups[resource]) groups[resource] = [];
    groups[resource].push(scope);
  }
  return groups;
});

function handleRoleDeleted() {
  router.push("/roles");
}
</script>

<template>
  <Spinner v-if="status.loading" />
  <div v-if="status.error" class="text-danger">{{ status.error }}</div>

  <div v-if="role?.id" class="card">
    <div class="card-header d-flex align-items-center justify-content-between">
      <div class="d-flex align-items-center gap-2">
        <span class="fw-semibold">{{ role.name }}</span>
        <span v-if="role.default_role" class="badge bg-success">default</span>
      </div>
      <RolesActions
        :role_id="role.id"
        :role_name="role.name"
        :default_actions="{ view: false }"
        @role-deleted="handleRoleDeleted"
      />
    </div>

    <div class="card-body">
      <div v-if="role.scopes.includes('*')">
        <span class="badge bg-danger fs-6">* — full access</span>
      </div>
      <div
        v-else-if="Object.keys(scopesByResource).length === 0"
        class="text-muted"
      >
        No scopes assigned.
      </div>
      <div v-else class="row g-2">
        <div
          v-for="(scopeList, resource) in scopesByResource"
          :key="resource"
          class="col-12 col-md-6 col-xl-4"
        >
          <div class="border rounded p-2 h-100">
            <p class="fw-semibold text-capitalize mb-1 small">
              {{ resource.replace(/_/g, " ") }}
            </p>
            <div class="d-flex flex-wrap gap-1">
              <span
                v-for="scope in scopeList"
                :key="scope"
                class="badge"
                :class="scope.endsWith(':*') ? 'bg-primary' : 'bg-secondary'"
              >
                {{ scope.split(":")[1] }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
