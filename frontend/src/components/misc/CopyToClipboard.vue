<script setup>

const props = defineProps(['value']);

function copyValueToClipboard() {
    navigator.clipboard.writeText(props.value);
}

</script>

<template>
    <button type="button" class="btn"><font-awesome-icon class="text-primary" icon="fa-solid fa-copy"
            @click="copyValueToClipboard" /></button>
</template>