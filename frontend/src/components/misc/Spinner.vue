<template>
  <div v-if="visible" class="spinner-overlay">
    <div class="spinner-border" role="status">
      <span class="visually-hidden">Loading...</span>
    </div>
  </div>
</template>

<script>
export default {
  name: "Spinner",
  data() {
    return {
      visible: false,
      timer: null,
    };
  },
  mounted() {
    this.timer = setTimeout(() => {
      this.visible = true;
    }, 100);
  },
  beforeUnmount() {
    clearTimeout(this.timer);
  },
};
</script>

<style scoped>
.spinner-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 1050;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  justify-content: center;
  align-items: center;
}
</style>
