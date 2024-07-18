<script setup>

const props = defineProps(['uuid']);

function copyUuidToClipboard() {
    navigator.clipboard.writeText(props.uuid);
}

</script>

<template>
    <span class="badge bg-light text-dark">{{ uuid }} </span>
    <button type="button" class="btn"><font-awesome-icon class="text-primary" icon="fa-solid fa-copy"
            @click="copyUuidToClipboard" /></button>
</template>