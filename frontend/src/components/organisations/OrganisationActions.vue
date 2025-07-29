<script setup>
import { authHelper } from "@/helpers";
import { ref, computed, onMounted } from "vue";
import { Modal } from "bootstrap";
import { storeToRefs } from "pinia";
import { useAuthStore, useUserSettingsStore } from "@/stores";
import DeleteOrganisationModal from "@/components/organisations/DeleteOrganisationModal.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faTrash,
  faEye,
  faPen,
  faBookmark,
} from "@fortawesome/free-solid-svg-icons";

const authStore = useAuthStore();
const { scopes } = storeToRefs(authStore);

const userSettingsStore = useUserSettingsStore();
const { userSettings } = storeToRefs(userSettingsStore);

const followed = ref(false);

const props = defineProps({
  organisation_uuid: String,
  default_actions: {
    type: Object,
    default: () => ({}),
  },
});

const actions = computed(() => ({
  index:
    props.default_actions.index ??
    authHelper.hasScope(scopes.value, "organisations:index"),
  view:
    props.default_actions.view ??
    authHelper.hasScope(scopes.value, "organisations:view"),
  update:
    props.default_actions.update ??
    authHelper.hasScope(scopes.value, "organisations:update"),
  delete:
    props.default_actions.delete ??
    authHelper.hasScope(scopes.value, "organisations:delete"),
}));

const deleteOrganisationModal = ref(null);

onMounted(() => {
  deleteOrganisationModal.value = new Modal(
    document.getElementById(
      `deleteOrganisationModal_${props.organisation_uuid}`,
    ),
  );
  userSettingsStore.getAll().then(() => {
    followed.value =
      userSettings.value.notifications?.follow?.organisations.includes(
        props.organisation_uuid,
      );
  });
});

function openDeleteOrganisationModal() {
  deleteOrganisationModal.value.show();
}

const emit = defineEmits(["organisation-updated", "organisation-deleted"]);

function handleOrganisationDeleted(event) {
  emit("organisation-deleted", event);
}

function followOrganisation() {
  followed.value = !followed.value;

  const followed_organisations =
    userSettings.value.notifications?.follow?.organisations || [];

  if (followed.value) {
    userSettingsStore.update("notifications", {
      follow: {
        organisations: followed_organisations.concat(props.organisation_uuid),
      },
    });
  } else {
    userSettingsStore.update("notifications", {
      follow: {
        organisations: followed_organisations.filter(
          (uuid) => uuid !== props.organisation_uuid,
        ),
      },
    });
  }
}
</script>

<style scoped>
.btn-toolbar {
  flex-wrap: nowrap !important;
}
</style>

<template>
  <div class="btn-toolbar float-end" role="toolbar">
    <div
      :class="{ 'btn-group-vertical': $isMobile, 'btn-group me-2': !$isMobile }"
      role="group"
      aria-label="Event Actions"
    >
      <RouterLink
        v-if="actions.view"
        :to="`/organisations/${organisation_uuid}`"
        class="btn btn-outline-primary"
        data-placement="top"
        data-toggle="tooltip"
        title="View Organisation"
      >
        <FontAwesomeIcon :icon="faEye" />
      </RouterLink>
      <RouterLink
        v-if="actions.update"
        :to="`/organisations/update/${organisation_uuid}`"
        class="btn btn-outline-primary"
        data-placement="top"
        data-toggle="tooltip"
        title="Update Organisation"
      >
        <FontAwesomeIcon :icon="faPen" />
      </RouterLink>
    </div>
    <div class="btn-group me-2" role="group">
      <button
        type="button"
        class="btn btn-outline-primary"
        data-placement="top"
        data-toggle="tooltip"
        title="Follow Organisation"
        @click="followOrganisation"
      >
        <FontAwesomeIcon
          v-if="!followed"
          :icon="faBookmark"
          :inverse="true"
          class="text-light"
        />
        <FontAwesomeIcon
          v-if="followed"
          :icon="faBookmark"
          class="text-success"
        />
      </button>
    </div>
    <div class="btn-group me-2" role="group">
      <button
        v-if="actions.delete"
        type="button"
        class="btn btn-danger"
        data-placement="top"
        data-toggle="tooltip"
        title="Delete Organisation"
        @click="openDeleteOrganisationModal"
      >
        <FontAwesomeIcon :icon="faTrash" />
      </button>
    </div>
  </div>
  <DeleteOrganisationModal
    :key="organisation_uuid"
    :id="`deleteOrganisationModal_${organisation_uuid}`"
    @organisation-deleted="handleOrganisationDeleted"
    :modal="deleteOrganisationModal"
    :organisation_uuid="organisation_uuid"
  />
</template>
