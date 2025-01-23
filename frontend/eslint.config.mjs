import pluginVue from "eslint-plugin-vue";
import {
  defineConfigWithVueTs,
  vueTsConfigs,
  configureVueProject,
} from "@vue/eslint-config-typescript";
import pluginPrettierRecommendedConfigs from "eslint-plugin-prettier/recommended";

configureVueProject({
  scriptLangs: ["ts", "js"],
  rootDir: import.meta.dirname,
});

export default defineConfigWithVueTs(
  pluginVue.configs["flat/essential"],
  vueTsConfigs.base,
  pluginPrettierRecommendedConfigs,
  // vueTsConfigs.recommended,
  {
    name: "app/files-to-ignore",
    ignores: [
      "**/node_modules/**",
      "**/dist/**",
      "**/dist/assets/**",
      "**/dist-ssr/**",
      "**/coverage/**",
    ],
    rules: {
      "vue/multi-word-component-names": "off",
      "vue/require-v-for-key": "off",
    },
  },
);
