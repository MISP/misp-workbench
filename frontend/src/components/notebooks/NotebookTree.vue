<script setup>
import { ref, onMounted, computed } from "vue";
import { storeToRefs } from "pinia";
import { useNotebooksStore, useToastsStore } from "@/stores";
import {
  faPlus,
  faFolder,
  faRotateRight,
  faFileImport,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import TreeNode from "./TreeNode.vue";
import NewFolderDialog from "./NewFolderDialog.vue";
import NewNotebookDialog from "./NewNotebookDialog.vue";

const props = defineProps({
  selectedNotebookId: { type: Number, default: null },
  currentUserId: { type: Number, default: null },
});
const emit = defineEmits(["select-notebook"]);

const notebooksStore = useNotebooksStore();
const toastsStore = useToastsStore();
const { tree, status } = storeToRefs(notebooksStore);

const newDialogVisibility = ref("personal");
const newDialogFolderId = ref(null);

function rootChildren(visibility) {
  const folders = (tree.value.folders || []).filter(
    (f) => f.visibility === visibility && f.parent_id == null,
  );
  const notebooks = (tree.value.notebooks || []).filter(
    (n) => n.visibility === visibility && n.folder_id == null,
  );
  return { folders, notebooks };
}

function buildChildren(folderId) {
  const folders = (tree.value.folders || []).filter(
    (f) => f.parent_id === folderId,
  );
  const notebooks = (tree.value.notebooks || []).filter(
    (n) => n.folder_id === folderId,
  );
  return { folders, notebooks };
}

const personal = computed(() => rootChildren("personal"));
const globalRoot = computed(() => rootChildren("global"));

function openNewFolder(visibility) {
  newDialogVisibility.value = visibility;
  newDialogFolderId.value = null;
}

function openNewNotebook(visibility) {
  newDialogVisibility.value = visibility;
  newDialogFolderId.value = null;
}

async function onCreateFolder(payload) {
  try {
    await notebooksStore.createFolder(payload);
    toastsStore.push(`Folder "${payload.name}" created.`, "success");
  } catch (err) {
    toastsStore.push(
      `Failed to create folder: ${err?.message || err}`,
      "danger",
    );
  }
}

async function onCreateNotebook(payload) {
  try {
    const nb = await notebooksStore.createNotebook(payload);
    toastsStore.push(`Notebook "${payload.name}" created.`, "success");
    emit("select-notebook", nb);
  } catch (err) {
    toastsStore.push(
      `Failed to create notebook: ${err?.message || err}`,
      "danger",
    );
  }
}

async function onDeleteFolder(folder) {
  if (!confirm(`Delete folder "${folder.name}"? Child notebooks survive.`))
    return;
  try {
    await notebooksStore.deleteFolder(folder.id);
    toastsStore.push(`Folder "${folder.name}" deleted.`, "success");
  } catch (err) {
    toastsStore.push(`Failed to delete: ${err?.message || err}`, "danger");
  }
}

async function onRenameFolder(folder) {
  const newName = prompt("New name:", folder.name);
  if (!newName || newName === folder.name) return;
  try {
    await notebooksStore.updateFolder(folder.id, { name: newName });
  } catch (err) {
    toastsStore.push(`Failed to rename: ${err?.message || err}`, "danger");
  }
}

async function onDeleteNotebook(notebook) {
  if (!confirm(`Delete notebook "${notebook.name}"?`)) return;
  try {
    await notebooksStore.deleteNotebook(notebook.id);
    toastsStore.push(`Notebook "${notebook.name}" deleted.`, "success");
    if (props.selectedNotebookId === notebook.id) {
      emit("select-notebook", null);
    }
  } catch (err) {
    toastsStore.push(`Failed to delete: ${err?.message || err}`, "danger");
  }
}

async function onRenameNotebook(notebook) {
  const newName = prompt("New name:", notebook.name);
  if (!newName || newName === notebook.name) return;
  try {
    await notebooksStore.updateNotebook(notebook.id, { name: newName });
    await notebooksStore.loadTree();
  } catch (err) {
    toastsStore.push(`Failed to rename: ${err?.message || err}`, "danger");
  }
}

async function onForkNotebook(notebook) {
  try {
    const fork = await notebooksStore.forkNotebook(notebook.id);
    toastsStore.push(`Forked "${notebook.name}" → "${fork.name}".`, "success");
    emit("select-notebook", fork);
  } catch (err) {
    toastsStore.push(`Failed to fork: ${err?.message || err}`, "danger");
  }
}

const importInput = ref(null);
function triggerImport() {
  importInput.value?.click();
}
async function onImportFile(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  try {
    const nb = await notebooksStore.importNotebook(file);
    toastsStore.push(`Imported "${nb.name}".`, "success");
    emit("select-notebook", nb);
  } catch (err) {
    toastsStore.push(`Import failed: ${err?.message || err}`, "danger");
  } finally {
    // Reset so re-importing the same file fires another change event.
    if (importInput.value) importInput.value.value = "";
  }
}

onMounted(() => {
  notebooksStore.loadTree();
});
</script>

<template>
  <aside class="notebook-tree d-flex flex-column h-100">
    <div class="tree-header d-flex align-items-center px-2 py-2 border-bottom">
      <strong class="small text-muted me-auto">Notebooks</strong>
      <button
        class="btn btn-link btn-sm p-1 text-secondary"
        title="Import .ipynb (creates a personal notebook)"
        @click="triggerImport"
      >
        <FontAwesomeIcon :icon="faFileImport" />
      </button>
      <button
        class="btn btn-link btn-sm p-1 text-secondary"
        title="Refresh"
        @click="notebooksStore.loadTree()"
        :disabled="status.loadingTree"
      >
        <FontAwesomeIcon :icon="faRotateRight" />
      </button>
      <input
        ref="importInput"
        type="file"
        accept=".ipynb,application/json"
        class="d-none"
        @change="onImportFile"
      />
    </div>

    <div v-if="status.error" class="alert alert-warning small m-2 py-2">
      {{ status.error }}
    </div>

    <div class="tree-body flex-grow-1 overflow-auto">
      <!-- Personal section -->
      <div class="tree-section">
        <div class="tree-section-header">
          <span class="me-auto">Personal</span>
          <button
            class="btn btn-link btn-sm p-0 text-secondary"
            data-bs-toggle="modal"
            data-bs-target="#newFolderModal-personal"
            title="New folder"
            @click="openNewFolder('personal')"
          >
            <FontAwesomeIcon :icon="faFolder" />
          </button>
          <button
            class="btn btn-link btn-sm p-0 ms-2 text-primary"
            data-bs-toggle="modal"
            data-bs-target="#newNotebookModal-personal"
            title="New notebook"
            @click="openNewNotebook('personal')"
          >
            <FontAwesomeIcon :icon="faPlus" />
          </button>
        </div>
        <ul class="list-unstyled m-0">
          <TreeNode
            v-for="f in personal.folders"
            :key="`f-${f.id}`"
            :node="{ kind: 'folder', folder: f }"
            :child-folders="buildChildren(f.id).folders"
            :child-notebooks="buildChildren(f.id).notebooks"
            :build-children="buildChildren"
            :selected-notebook-id="selectedNotebookId"
            :current-user-id="currentUserId"
            @select-notebook="(n) => $emit('select-notebook', n)"
            @delete-folder="onDeleteFolder"
            @rename-folder="onRenameFolder"
            @delete-notebook="onDeleteNotebook"
            @rename-notebook="onRenameNotebook"
            @fork-notebook="onForkNotebook"
          />
          <TreeNode
            v-for="n in personal.notebooks"
            :key="`n-${n.id}`"
            :node="{ kind: 'notebook', notebook: n }"
            :build-children="buildChildren"
            :selected-notebook-id="selectedNotebookId"
            :current-user-id="currentUserId"
            @select-notebook="(nb) => $emit('select-notebook', nb)"
            @delete-folder="onDeleteFolder"
            @rename-folder="onRenameFolder"
            @delete-notebook="onDeleteNotebook"
            @rename-notebook="onRenameNotebook"
            @fork-notebook="onForkNotebook"
          />
        </ul>
      </div>

      <!-- Global section -->
      <div class="tree-section">
        <div class="tree-section-header">
          <span class="me-auto">Global</span>
          <button
            class="btn btn-link btn-sm p-0 text-secondary"
            data-bs-toggle="modal"
            data-bs-target="#newFolderModal-global"
            title="New folder"
            @click="openNewFolder('global')"
          >
            <FontAwesomeIcon :icon="faFolder" />
          </button>
          <button
            class="btn btn-link btn-sm p-0 ms-2 text-primary"
            data-bs-toggle="modal"
            data-bs-target="#newNotebookModal-global"
            title="New notebook"
            @click="openNewNotebook('global')"
          >
            <FontAwesomeIcon :icon="faPlus" />
          </button>
        </div>
        <ul class="list-unstyled m-0">
          <TreeNode
            v-for="f in globalRoot.folders"
            :key="`f-${f.id}`"
            :node="{ kind: 'folder', folder: f }"
            :child-folders="buildChildren(f.id).folders"
            :child-notebooks="buildChildren(f.id).notebooks"
            :build-children="buildChildren"
            :selected-notebook-id="selectedNotebookId"
            :current-user-id="currentUserId"
            @select-notebook="(n) => $emit('select-notebook', n)"
            @delete-folder="onDeleteFolder"
            @rename-folder="onRenameFolder"
            @delete-notebook="onDeleteNotebook"
            @rename-notebook="onRenameNotebook"
            @fork-notebook="onForkNotebook"
          />
          <TreeNode
            v-for="n in globalRoot.notebooks"
            :key="`n-${n.id}`"
            :node="{ kind: 'notebook', notebook: n }"
            :build-children="buildChildren"
            :selected-notebook-id="selectedNotebookId"
            :current-user-id="currentUserId"
            @select-notebook="(nb) => $emit('select-notebook', nb)"
            @delete-folder="onDeleteFolder"
            @rename-folder="onRenameFolder"
            @delete-notebook="onDeleteNotebook"
            @rename-notebook="onRenameNotebook"
            @fork-notebook="onForkNotebook"
          />
        </ul>
      </div>
    </div>

    <NewFolderDialog
      modal-id="newFolderModal-personal"
      visibility="personal"
      @create="onCreateFolder"
    />
    <NewFolderDialog
      modal-id="newFolderModal-global"
      visibility="global"
      @create="onCreateFolder"
    />
    <NewNotebookDialog
      modal-id="newNotebookModal-personal"
      visibility="personal"
      @create="onCreateNotebook"
    />
    <NewNotebookDialog
      modal-id="newNotebookModal-global"
      visibility="global"
      @create="onCreateNotebook"
    />
  </aside>
</template>

<style scoped>
.notebook-tree {
  width: 280px;
  min-width: 280px;
  border-right: 1px solid var(--bs-border-color, #dee2e6);
  background: var(--bs-body-bg, #fff);
}
.tree-section {
  padding: 4px 0;
}
.tree-section-header {
  display: flex;
  align-items: center;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--bs-secondary-color, #6c757d);
  padding: 6px 10px;
  background: var(--bs-tertiary-bg, #f8f9fa);
}
</style>
