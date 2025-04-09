import { ref, watch } from "vue";

export function useLocalStorageRef(key, defaultValue) {
  const storedValue = localStorage.getItem(key);
  const data = ref(
    storedValue !== null ? JSON.parse(storedValue) : defaultValue,
  );

  watch(
    data,
    (newVal) => {
      localStorage.setItem(key, JSON.stringify(newVal));
    },
    { deep: true },
  );

  return data;
}
