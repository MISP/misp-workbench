<script setup>
defineProps(['tags']);
</script>

<template>
    <div class="col-auto">
        <span class="badge mx-1" v-for="tag in tags" :style="{ backgroundColor: tag.colour }">{{ tag.name }}</span>
    </div>
</template>