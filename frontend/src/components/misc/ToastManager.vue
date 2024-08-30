<script setup>
import { useToastsStore } from "@/stores";
import { storeToRefs } from 'pinia'

const toastsStore = useToastsStore();
const { toasts } = storeToRefs(toastsStore);

const removeToast = (id) => {
    toastsStore.remove(id);
};
</script>

<template>
    <div class="toast-container position-fixed bottom-0 end-0 p-3">
        <div v-for="toast in toasts" :key="toast.id" class="toast align-items-center border-0 show mb-2"
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
