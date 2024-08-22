<script setup>
import { ref } from 'vue';
import { useToastsStore } from "@/stores";

const toastsStore = useToastsStore();
import { storeToRefs } from 'pinia'
const { toasts } = storeToRefs(toastsStore);

const removeToast = (id) => {
    toastsStore.remove(id);
};
</script>

<style scoped></style>

<template>
    <div class="toast-container position-fixed bottom-0 end-0 p-3">
        <div v-for="toast in toasts" :key="index" class="toast align-items-center border-0 show mb-2"
            :class="toast.type" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    {{ toast.message }}
                </div>
                <button type="button" class="btn-close me-2 m-auto" @click="removeToast(toast.id)"
                    aria-label="Close"></button>
            </div>
        </div>
    </div>
</template>
