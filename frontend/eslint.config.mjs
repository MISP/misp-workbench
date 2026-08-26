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
  {
    name: "app/files-to-lint",
    files: ["**/*.{ts,mts,tsx,vue}"],
  },
  {
    name: "app/files-to-ignore",
    ignores: [
      "**/dist/**",
      "**/dist-ssr/**",
      "**/coverage/**",
      // Vendored third party source, linted by its own project.
      "submodules/**",
    ],
  },
  pluginVue.configs["flat/essential"],
  vueTsConfigs.base,
  pluginPrettierRecommendedConfigs,
  vueTsConfigs.recommended,
  {
    name: "app/rules",
    rules: {
      "vue/multi-word-component-names": "off",
      "vue/require-v-for-key": "off",
    },
  },
);
