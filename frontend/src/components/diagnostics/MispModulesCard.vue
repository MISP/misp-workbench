<script setup>
import { ref } from "vue";
import { storeToRefs } from "pinia";
import { useDiagnosticsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";

const store = useDiagnosticsStore();
const { modules, status } = storeToRefs(store);

const search = ref("");
const filterType = ref("");

function filteredModules() {
  if (!modules.value?.modules) return [];
  return modules.value.modules.filter((m) => {
    const matchesType = !filterType.value || m.type === filterType.value;
    const matchesSearch =
      !search.value ||
      m.name?.toLowerCase().includes(search.value.toLowerCase()) ||
      m.meta_name?.toLowerCase().includes(search.value.toLowerCase()) ||
      m.description?.toLowerCase().includes(search.value.toLowerCase());
    return matchesType && matchesSearch;
  });
}

function typeBadgeClass(type) {
  switch (type) {
    case "expansion":
      return "bg-primary";
    case "import_mod":
      return "bg-info text-dark";
    case "export_mod":
      return "bg-warning text-dark";
    case "action_mod":
      return "bg-secondary";
    default:
      return "bg-light text-dark";
  }
}

function typeLabel(type) {
  switch (type) {
    case "expansion":
      return "expansion";
    case "import_mod":
      return "import";
    case "export_mod":
      return "export";
    case "action_mod":
      return "action";
    default:
      return type;
  }
}
</script>

<template>
  <div class="card my-3 shadow">
    <div class="card-header d-flex align-items-center">
      <h5 class="mb-0">MISP Modules</h5>
      <span
        v-if="modules"
        class="ms-2 badge"
        :class="modules.connected ? 'bg-success' : 'bg-danger'"
      >
        {{ modules.connected ? "connected" : "unreachable" }}
      </span>
      <span v-if="modules?.connected" class="ms-2 badge bg-secondary">
        {{ modules.total }} modules
      </span>
    </div>
    <div class="card-body">
      <Spinner v-if="status.loading" />

      <div v-if="!status.loading && modules">
        <div v-if="!modules.connected" class="alert alert-danger mb-0">
          Cannot reach <code>{{ modules.url }}</code
          >: {{ modules.error }}
        </div>

        <template v-else>
          <!-- Summary counts -->
          <ul class="list-group list-group-flush small mb-3">
            <li class="list-group-item d-flex justify-content-between">
              <span>Endpoint</span>
              <span class="text-muted text-console">{{ modules.url }}</span>
            </li>
            <li
              v-for="(count, type) in modules.counts"
              :key="type"
              class="list-group-item d-flex justify-content-between"
            >
              <span>
                <span class="badge me-1" :class="typeBadgeClass(type)">{{
                  typeLabel(type)
                }}</span>
              </span>
              <span class="text-muted">{{ count }}</span>
            </li>
          </ul>

          <!-- Module list -->
          <div class="card mt-2">
            <div class="card-header d-flex align-items-center gap-2">
              <h6 class="mb-0 me-auto">Modules</h6>
              <select
                v-model="filterType"
                class="form-select form-select-sm"
                style="width: auto"
              >
                <option value="">All types</option>
                <option
                  v-for="(count, type) in modules.counts"
                  :key="type"
                  :value="type"
                >
                  {{ typeLabel(type) }} ({{ count }})
                </option>
              </select>
              <input
                v-model="search"
                type="text"
                class="form-control form-control-sm"
                placeholder="Search..."
                style="width: 200px"
              />
            </div>
            <div class="table-responsive" style="max-height: 400px">
              <table class="table table-sm table-bordered small mb-0">
                <thead class="table sticky-top">
                  <tr>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Description</th>
                    <th>Version</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="m in filteredModules()" :key="m.name">
                    <td class="text-console text-nowrap">
                      {{ m.meta_name || m.name }}
                    </td>
                    <td>
                      <span
                        v-for="t in m.module_type"
                        :key="t"
                        class="badge me-1"
                        :class="typeBadgeClass(m.type)"
                      >
                        {{ t }}
                      </span>
                    </td>
                    <td class="text-muted">{{ m.description }}</td>
                    <td class="text-center">{{ m.version }}</td>
                  </tr>
                  <tr v-if="filteredModules().length === 0">
                    <td colspan="4" class="text-muted text-center">
                      No modules match the current filter.
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>
