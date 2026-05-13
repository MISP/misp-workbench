<script setup>
import { ref, watch, onMounted } from "vue";
import { useRouter } from "vue-router";
import { fetchWrapper } from "@/helpers";
import NotebookTree from "@/components/notebooks/NotebookTree.vue";
import NotebookEditor from "@/components/notebooks/NotebookEditor.vue";

const props = defineProps({
  id: { type: [String, Number], default: null },
});

const router = useRouter();
const selectedNotebookId = ref(props.id != null ? Number(props.id) : null);
const currentUserId = ref(null);

watch(
  () => props.id,
  (newId) => {
    selectedNotebookId.value = newId != null ? Number(newId) : null;
  },
);

onMounted(async () => {
  // The JWT only carries the user's email + scopes; we need the user id for
  // ownership checks (read-only badge, fork CTA, edit-action visibility).
  try {
    const me = await fetchWrapper.get(
      `${import.meta.env.VITE_API_URL}/users/me`,
    );
    currentUserId.value = me?.id ?? null;
  } catch {
    currentUserId.value = null;
  }
});

function onSelectNotebook(notebook) {
  if (notebook == null) {
    selectedNotebookId.value = null;
    router.replace("/tech-lab/notebooks");
    return;
  }
  selectedNotebookId.value = notebook.id;
  router.replace(`/tech-lab/notebooks/${notebook.id}`);
}
</script>

<template>
  <div class="notebooks-workspace d-flex">
    <NotebookTree
      :selected-notebook-id="selectedNotebookId"
      :current-user-id="currentUserId"
      @select-notebook="onSelectNotebook"
    />
    <NotebookEditor
      :notebook-id="selectedNotebookId"
      :current-user-id="currentUserId"
      @select-notebook="onSelectNotebook"
    />
  </div>
</template>

<style scoped>
.notebooks-workspace {
  height: calc(100vh - 56px); /* full viewport minus app navbar */
  width: 100%;
}
</style>
