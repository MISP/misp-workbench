<script setup>
import { ref, onMounted, computed } from "vue";
import { storeToRefs } from "pinia";
import { useNotebooksStore, useToastsStore } from "@/stores";
import {
  faPlus,
  faFolder,
  faRotateRight,
  faFileImport,
  faBookOpen,
  faMagnifyingGlass,
  faThumbtack,
  faXmark,
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

const query = ref("");
const hasQuery = computed(() => query.value.trim().length > 0);
function nameMatches(name) {
  if (!hasQuery.value) return true;
  return (name || "").toLowerCase().includes(query.value.trim().toLowerCase());
}

// Set of folder ids that should remain visible under the current search. A
// folder qualifies if its own name matches OR any descendant (folder /
// notebook) name matches. Returns null when there is no query so callers can
// skip the filter cheaply.
const visibleFolderIds = computed(() => {
  if (!hasQuery.value) return null;
  const folders = tree.value.folders || [];
  const notebooks = tree.value.notebooks || [];
  const foldersByParent = new Map();
  for (const f of folders) {
    const key = f.parent_id ?? null;
    if (!foldersByParent.has(key)) foldersByParent.set(key, []);
    foldersByParent.get(key).push(f);
  }
  const notebooksByFolder = new Map();
  for (const n of notebooks) {
    if (n.folder_id == null) continue;
    if (!notebooksByFolder.has(n.folder_id))
      notebooksByFolder.set(n.folder_id, []);
    notebooksByFolder.get(n.folder_id).push(n);
  }
  const visible = new Set();
  function visit(folder) {
    let hit = nameMatches(folder.name);
    for (const cf of foldersByParent.get(folder.id) || []) {
      if (visit(cf)) hit = true;
    }
    for (const n of notebooksByFolder.get(folder.id) || []) {
      if (nameMatches(n.name)) hit = true;
    }
    if (hit) visible.add(folder.id);
    return hit;
  }
  for (const f of folders.filter((x) => x.parent_id == null)) visit(f);
  return visible;
});

function rootChildren(visibility) {
  const folders = (tree.value.folders || []).filter(
    (f) =>
      f.visibility === visibility &&
      f.parent_id == null &&
      (!visibleFolderIds.value || visibleFolderIds.value.has(f.id)),
  );
  const notebooks = (tree.value.notebooks || []).filter(
    (n) =>
      n.visibility === visibility && n.folder_id == null && nameMatches(n.name),
  );
  return { folders, notebooks };
}

function buildChildren(folderId) {
  const folders = (tree.value.folders || []).filter(
    (f) =>
      f.parent_id === folderId &&
      (!visibleFolderIds.value || visibleFolderIds.value.has(f.id)),
  );
  const notebooks = (tree.value.notebooks || []).filter(
    (n) => n.folder_id === folderId && nameMatches(n.name),
  );
  return { folders, notebooks };
}

const personal = computed(() => rootChildren("personal"));
const globalRoot = computed(() => rootChildren("global"));
const library = computed(() => rootChildren("library"));

const pinned = computed(() =>
  (tree.value.notebooks || [])
    .filter((n) => n.is_pinned && nameMatches(n.name))
    .sort((a, b) => a.name.localeCompare(b.name)),
);

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

async function onTogglePin(notebook) {
  try {
    await notebooksStore.togglePin(notebook.id, !notebook.is_pinned);
  } catch (err) {
    toastsStore.push(`Failed to pin: ${err?.message || err}`, "danger");
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

    <div class="tree-search px-2 py-2 border-bottom">
      <div class="input-group input-group-sm">
        <span class="input-group-text bg-body">
          <FontAwesomeIcon :icon="faMagnifyingGlass" class="text-muted" />
        </span>
        <input
          v-model="query"
          type="search"
          class="form-control"
          placeholder="Search notebooks…"
          aria-label="Search notebooks"
        />
        <button
          v-if="hasQuery"
          class="btn btn-outline-secondary"
          type="button"
          title="Clear"
          @click="query = ''"
        >
          <FontAwesomeIcon :icon="faXmark" />
        </button>
      </div>
    </div>

    <div v-if="status.error" class="alert alert-warning small m-2 py-2">
      {{ status.error }}
    </div>

    <div class="tree-body flex-grow-1 overflow-auto">
      <!-- Pinned section (personal notebooks the user has pinned) -->
      <div v-if="pinned.length > 0" class="tree-section">
        <div class="tree-section-header">
          <FontAwesomeIcon :icon="faThumbtack" class="me-2 text-warning" />
          <span class="me-auto">Pinned</span>
        </div>
        <ul class="list-unstyled m-0">
          <TreeNode
            v-for="n in pinned"
            :key="`pin-${n.id}`"
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
            @toggle-pin="onTogglePin"
          />
        </ul>
      </div>

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
            :force-open="hasQuery"
            @select-notebook="(n) => $emit('select-notebook', n)"
            @delete-folder="onDeleteFolder"
            @rename-folder="onRenameFolder"
            @delete-notebook="onDeleteNotebook"
            @rename-notebook="onRenameNotebook"
            @fork-notebook="onForkNotebook"
            @toggle-pin="onTogglePin"
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
            @toggle-pin="onTogglePin"
          />
        </ul>
      </div>

      <!-- Library section (read-only prebuilt notebooks; users fork to run) -->
      <div class="tree-section">
        <div
          class="tree-section-header"
          title="Read-only prebuilt notebooks. Fork them to a personal copy to run or edit."
        >
          <FontAwesomeIcon :icon="faBookOpen" class="me-2 text-muted" />
          <span class="me-auto">Library</span>
        </div>
        <div
          v-if="library.folders.length === 0 && library.notebooks.length === 0"
          class="text-muted small fst-italic px-3 py-1"
        >
          No library notebooks. Seed via
          <code>python -m app.cli seed-lab-library</code>
        </div>
        <ul class="list-unstyled m-0">
          <TreeNode
            v-for="f in library.folders"
            :key="`f-${f.id}`"
            :node="{ kind: 'folder', folder: f }"
            :child-folders="buildChildren(f.id).folders"
            :child-notebooks="buildChildren(f.id).notebooks"
            :build-children="buildChildren"
            :selected-notebook-id="selectedNotebookId"
            :current-user-id="currentUserId"
            :force-open="hasQuery"
            @select-notebook="(n) => $emit('select-notebook', n)"
            @delete-folder="onDeleteFolder"
            @rename-folder="onRenameFolder"
            @delete-notebook="onDeleteNotebook"
            @rename-notebook="onRenameNotebook"
            @fork-notebook="onForkNotebook"
            @toggle-pin="onTogglePin"
          />
          <TreeNode
            v-for="n in library.notebooks"
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
            @toggle-pin="onTogglePin"
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
            :force-open="hasQuery"
            @select-notebook="(n) => $emit('select-notebook', n)"
            @delete-folder="onDeleteFolder"
            @rename-folder="onRenameFolder"
            @delete-notebook="onDeleteNotebook"
            @rename-notebook="onRenameNotebook"
            @fork-notebook="onForkNotebook"
            @toggle-pin="onTogglePin"
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
            @toggle-pin="onTogglePin"
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
