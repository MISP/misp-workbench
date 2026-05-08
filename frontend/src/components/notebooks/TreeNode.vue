<script setup>
import { computed, ref } from "vue";
import {
  faFolder,
  faFolderOpen,
  faFile,
  faChevronRight,
  faChevronDown,
  faTrash,
  faPen,
  faCodeBranch,
  faLock,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

const props = defineProps({
  // One of: { kind: "folder", folder } / { kind: "notebook", notebook }
  node: { type: Object, required: true },
  // Pre-grouped children (only relevant for folders)
  childFolders: { type: Array, default: () => [] },
  childNotebooks: { type: Array, default: () => [] },
  // For nested rendering: function that returns children for a given folder id.
  buildChildren: { type: Function, required: true },
  selectedNotebookId: { type: Number, default: null },
  currentUserId: { type: Number, default: null },
  depth: { type: Number, default: 0 },
});

const emit = defineEmits([
  "select-notebook",
  "delete-folder",
  "rename-folder",
  "delete-notebook",
  "rename-notebook",
  "fork-notebook",
]);

const open = ref(props.depth < 1);

const isFolder = computed(() => props.node.kind === "folder");
const isNotebook = computed(() => props.node.kind === "notebook");
const isSelected = computed(
  () => isNotebook.value && props.selectedNotebookId === props.node.notebook.id,
);
const visibility = computed(() =>
  isFolder.value
    ? props.node.folder.visibility
    : props.node.notebook.visibility,
);
const isLibrary = computed(() => visibility.value === "library");
const isOwned = computed(() => {
  if (isLibrary.value) return false; // library is read-only regardless of seed owner
  if (props.currentUserId == null) return true;
  const owner = isFolder.value
    ? props.node.folder.user_id
    : props.node.notebook.user_id;
  return owner === props.currentUserId;
});

function toggle() {
  if (isFolder.value) open.value = !open.value;
}

function onClick() {
  if (isNotebook.value) {
    emit("select-notebook", props.node.notebook);
  } else {
    toggle();
  }
}
</script>

<template>
  <li class="tree-node">
    <div
      class="tree-row"
      :class="{
        selected: isSelected,
        readonly: !isOwned,
      }"
      @click="onClick"
      :style="{ paddingLeft: `${depth * 14 + 6}px` }"
    >
      <span v-if="isFolder" class="chev me-1" @click.stop="toggle">
        <FontAwesomeIcon :icon="open ? faChevronDown : faChevronRight" />
      </span>
      <span v-else class="chev me-1 invisible">
        <FontAwesomeIcon :icon="faChevronRight" />
      </span>

      <FontAwesomeIcon
        :icon="isFolder ? (open ? faFolderOpen : faFolder) : faFile"
        class="me-2"
        :class="isFolder ? 'text-warning' : 'text-secondary'"
      />

      <span class="tree-label flex-grow-1">
        <template v-if="isFolder">{{ node.folder.name }}</template>
        <template v-else>{{ node.notebook.name }}</template>
        <FontAwesomeIcon
          v-if="isLibrary"
          :icon="faLock"
          class="ms-1 text-muted"
          title="Library notebook — fork to edit or run"
          style="font-size: 0.7rem"
        />
      </span>

      <span class="tree-actions">
        <button
          v-if="isNotebook && !isOwned"
          class="btn btn-link btn-sm p-0 ms-1 text-info"
          title="Fork to personal"
          @click.stop="$emit('fork-notebook', node.notebook)"
        >
          <FontAwesomeIcon :icon="faCodeBranch" />
        </button>
        <button
          v-if="isOwned"
          class="btn btn-link btn-sm p-0 ms-1 text-secondary"
          title="Rename"
          @click.stop="
            isFolder
              ? $emit('rename-folder', node.folder)
              : $emit('rename-notebook', node.notebook)
          "
        >
          <FontAwesomeIcon :icon="faPen" />
        </button>
        <button
          v-if="isOwned"
          class="btn btn-link btn-sm p-0 ms-1 text-danger"
          title="Delete"
          @click.stop="
            isFolder
              ? $emit('delete-folder', node.folder)
              : $emit('delete-notebook', node.notebook)
          "
        >
          <FontAwesomeIcon :icon="faTrash" />
        </button>
      </span>
    </div>

    <ul v-if="isFolder && open" class="tree-children list-unstyled mb-0">
      <TreeNode
        v-for="cf in childFolders"
        :key="`f-${cf.id}`"
        :node="{ kind: 'folder', folder: cf }"
        :child-folders="buildChildren(cf.id).folders"
        :child-notebooks="buildChildren(cf.id).notebooks"
        :build-children="buildChildren"
        :selected-notebook-id="selectedNotebookId"
        :current-user-id="currentUserId"
        :depth="depth + 1"
        @select-notebook="(n) => $emit('select-notebook', n)"
        @delete-folder="(f) => $emit('delete-folder', f)"
        @rename-folder="(f) => $emit('rename-folder', f)"
        @delete-notebook="(n) => $emit('delete-notebook', n)"
        @rename-notebook="(n) => $emit('rename-notebook', n)"
        @fork-notebook="(n) => $emit('fork-notebook', n)"
      />
      <TreeNode
        v-for="cn in childNotebooks"
        :key="`n-${cn.id}`"
        :node="{ kind: 'notebook', notebook: cn }"
        :build-children="buildChildren"
        :selected-notebook-id="selectedNotebookId"
        :current-user-id="currentUserId"
        :depth="depth + 1"
        @select-notebook="(n) => $emit('select-notebook', n)"
        @delete-folder="(f) => $emit('delete-folder', f)"
        @rename-folder="(f) => $emit('rename-folder', f)"
        @delete-notebook="(n) => $emit('delete-notebook', n)"
        @rename-notebook="(n) => $emit('rename-notebook', n)"
        @fork-notebook="(n) => $emit('fork-notebook', n)"
      />
    </ul>
  </li>
</template>

<style scoped>
.tree-row {
  display: flex;
  align-items: center;
  padding: 4px 6px;
  cursor: pointer;
  user-select: none;
  border-radius: 4px;
  font-size: 0.875rem;
}
.tree-row:hover {
  background: var(--bs-tertiary-bg, #eee);
}
.tree-row.selected {
  background: var(--bs-primary-bg-subtle, #cfe2ff);
}
.tree-row.readonly .tree-label {
  font-style: italic;
  opacity: 0.85;
}
.chev {
  width: 12px;
  display: inline-flex;
  justify-content: center;
  cursor: pointer;
  font-size: 0.65rem;
}
.tree-actions {
  visibility: hidden;
}
.tree-row:hover .tree-actions {
  visibility: visible;
}
.tree-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tree-children {
  margin: 0;
  padding: 0;
}
</style>
