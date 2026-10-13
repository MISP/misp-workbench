<script setup>
import { ref } from "vue";
import { useDetectionProfilesStore } from "@/stores";
import ProfileForm from "@/components/profiles/ProfileForm.vue";
import Spinner from "@/components/misc/Spinner.vue";

const props = defineProps(["id"]);
const profile = ref(null);
const error = ref(null);

useDetectionProfilesStore()
  .get(props.id)
  .then((p) => (profile.value = p))
  .catch((e) => (error.value = e));
</script>

<template>
  <div v-if="error" class="alert alert-danger">{{ error }}</div>
  <ProfileForm v-else-if="profile" :profile="profile" />
  <Spinner v-else />
</template>
