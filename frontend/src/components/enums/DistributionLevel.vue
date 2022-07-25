<script setup>
import { DISTRIBUTION_LEVEL } from "@/helpers/constants";
defineProps(['distribution_level_id']);
</script>

<template>
    <span v-if="distribution_level_id === DISTRIBUTION_LEVEL.ORGANISATION_ONLY">ORGANISATION_ONLY</span>
    <span v-if="distribution_level_id === DISTRIBUTION_LEVEL.COMMUNITY_ONLY">COMMUNITY_ONLY</span>
    <span v-if="distribution_level_id === DISTRIBUTION_LEVEL.CONNECTED_COMMUNITIES">CONNECTED_COMMUNITIES</span>
    <span v-if="distribution_level_id === DISTRIBUTION_LEVEL.ALL_COMMUNITIES">ALL_COMMUNITIES</span>
    <span v-if="distribution_level_id === DISTRIBUTION_LEVEL.SHARING_GROUP">SHARING_GROUP</span>
    <span v-if="distribution_level_id === DISTRIBUTION_LEVEL.INHERIT_EVENT">INHERIT_EVENT</span>
</template>