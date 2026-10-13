<script setup>
import { reactive, ref, computed, watch } from "vue";
import { router } from "@/router";
import {
  useDetectionProfilesStore,
  useIndicatorsStore,
  useToastsStore,
} from "@/stores";
import TagsSelect from "@/components/tags/TagsSelect.vue";
import AttributeTypeMultiSelect from "@/components/enums/AttributeTypeMultiSelect.vue";
import ScoreBadge from "@/components/indicators/ScoreBadge.vue";

// With `profile` the form edits it; without, it creates a new one.
const props = defineProps({ profile: { type: Object, default: null } });

const profilesStore = useDetectionProfilesStore();
const indicatorsStore = useIndicatorsStore();
const toastsStore = useToastsStore();

const TLPS = ["tlp:clear", "tlp:green", "tlp:amber", "tlp:amber+strict"];
const DEFAULT_RULES = {
  types: [],
  categories: [],
  tlp_ceiling: "tlp:amber",
  tags: [],
  exclude_tags: [],
  min_score: 50,
  max_age_days: null,
  sources: [],
  exclude_sources: [],
  organisations: [],
  exclude_organisations: [],
  min_source_trust: null,
  to_ids: true,
  exclude_warninglisted: true,
  exclude_validation_issues: true,
};

const form = reactive({
  name: props.profile?.name ?? "",
  description: props.profile?.description ?? "",
  granularity: props.profile?.granularity ?? "indicators",
});
const rules = reactive({
  ...DEFAULT_RULES,
  ...(props.profile?.rules ?? {}),
});
const categoriesText = ref((rules.categories || []).join(", "));
watch(categoriesText, (text) => {
  rules.categories = text
    .split(",")
    .map((c) => c.trim())
    .filter(Boolean);
});

const isEdit = computed(() => !!props.profile);
const apiError = ref(null);

// Sources and organisations to pick from: those with indicators.
const known = ref({ sources: [], organisations: [] });
indicatorsStore
  .sourceQuality()
  .then((report) => (known.value = report))
  .catch(() => {});

function toggle(list, key) {
  const i = list.indexOf(key);
  if (i >= 0) list.splice(i, 1);
  else list.push(key);
}

const asTagObjects = (names) =>
  names.map((name) => ({ id: null, name, colour: "#6c757d" }));
const includeTagObjects = computed(() => asTagObjects(rules.tags));
const excludeTagObjects = computed(() => asTagObjects(rules.exclude_tags));

function payloadRules() {
  return {
    ...rules,
    min_score: rules.min_score === "" ? null : rules.min_score,
    max_age_days: rules.max_age_days === "" ? null : rules.max_age_days,
    min_source_trust:
      rules.min_source_trust === "" ? null : rules.min_source_trust,
    tlp_ceiling: rules.tlp_ceiling || null,
  };
}

// The live count, refreshed as the rules change.
const preview = ref(null);
const previewError = ref(null);
let previewTimer = null;
watch(
  rules,
  () => {
    clearTimeout(previewTimer);
    previewTimer = setTimeout(async () => {
      try {
        preview.value = await profilesStore.preview(payloadRules());
        previewError.value = null;
      } catch (error) {
        previewError.value = error;
      }
    }, 400);
  },
  { deep: true, immediate: true },
);

async function submit() {
  apiError.value = null;
  const payload = { ...form, rules: payloadRules() };
  try {
    if (isEdit.value) {
      await profilesStore.update(props.profile.id, payload);
      toastsStore.push(`Profile "${form.name}" saved.`, "success");
    } else {
      await profilesStore.create(payload);
      toastsStore.push(`Profile "${form.name}" created.`, "success");
    }
    router.push("/detection-profiles");
  } catch (error) {
    apiError.value = error?.message || String(error);
  }
}
</script>

<template>
  <div class="card mx-auto" style="max-width: 900px">
    <div class="card-header border-bottom">
      <h4 class="mb-0">
        {{ isEdit ? `Edit "${profile.name}"` : "New detection profile" }}
      </h4>
    </div>
    <div class="card-body">
      <p class="text-muted">
        What goes to one kind of security control, defined once. Exports, feeds,
        sinks, lookups and restSearch can use it in place of their own filters.
        Every rule narrows the selection.
      </p>

      <div class="alert" :class="previewError ? 'alert-danger' : 'alert-info'">
        <div v-if="previewError">{{ previewError }}</div>
        <div v-else-if="preview">
          <strong id="profile-count">{{
            preview.count.toLocaleString()
          }}</strong>
          indicators match right now.
        </div>
        <div v-else>Counting…</div>
        <div v-if="preview?.sample?.length" class="small mt-1 text-break">
          <span
            v-for="s in preview.sample.slice(0, 3)"
            :key="s.uuid"
            class="font-monospace me-3 d-inline-block"
            ><ScoreBadge :score="s.score" class="me-1" />{{ s.value }}</span
          >
        </div>
      </div>

      <div class="row g-3 mb-3">
        <div class="col-md-6">
          <label class="form-label" for="profile-name">Name</label>
          <input
            id="profile-name"
            class="form-control"
            v-model="form.name"
            placeholder="Firewall block list"
          />
        </div>
        <div class="col-md-6">
          <label class="form-label" for="profile-granularity">Sends</label>
          <select
            id="profile-granularity"
            class="form-select"
            v-model="form.granularity"
          >
            <option value="indicators">
              Consolidated indicators (each value once)
            </option>
            <option value="attributes">
              Attributes (every attribute behind them)
            </option>
          </select>
        </div>
        <div class="col-12">
          <label class="form-label" for="profile-description"
            >Description</label
          >
          <input
            id="profile-description"
            class="form-control"
            v-model="form.description"
          />
        </div>
      </div>

      <h6 class="fw-semibold">What</h6>
      <div class="row g-3 mb-3">
        <div class="col-md-6">
          <label class="form-label">Types</label>
          <AttributeTypeMultiSelect
            :selected="rules.types"
            @update:selected="rules.types = $event"
          />
          <div class="form-text">Empty: every type.</div>
        </div>
        <div class="col-md-6">
          <label class="form-label" for="profile-categories">Categories</label>
          <input
            id="profile-categories"
            class="form-control"
            v-model="categoriesText"
            placeholder="Network activity, Payload delivery"
          />
          <div class="form-text">Comma-separated. Empty: every category.</div>
        </div>
      </div>

      <h6 class="fw-semibold">Sharing and tags</h6>
      <div class="row g-3 mb-3">
        <div class="col-md-4">
          <label class="form-label" for="profile-tlp">TLP ceiling</label>
          <select
            id="profile-tlp"
            class="form-select"
            v-model="rules.tlp_ceiling"
          >
            <option :value="null">none (tlp:red too)</option>
            <option v-for="t in TLPS" :key="t" :value="t">{{ t }}</option>
          </select>
          <div class="form-text">The most restrictive TLP let through.</div>
        </div>
        <div class="col-md-8">
          <label class="form-label">Only with tags</label>
          <TagsSelect
            modelClass="event"
            :persist="false"
            :selectedTags="includeTagObjects"
            @update:selectedTags="rules.tags = $event"
          />
          <label class="form-label mt-2">Never with tags</label>
          <TagsSelect
            modelClass="event"
            :persist="false"
            :selectedTags="excludeTagObjects"
            @update:selectedTags="rules.exclude_tags = $event"
          />
          <div class="form-text">
            Patterns work: <code>misp-galaxy:threat-actor=*</code>,
            <code>workbench:validation=*</code>.
          </div>
        </div>
      </div>

      <h6 class="fw-semibold">Quality</h6>
      <div class="row g-3 mb-3">
        <div class="col-md-4">
          <label class="form-label" for="profile-min-score"
            >Minimum score</label
          >
          <input
            id="profile-min-score"
            type="number"
            min="0"
            max="100"
            class="form-control"
            v-model.number="rules.min_score"
            placeholder="any"
          />
        </div>
        <div class="col-md-4">
          <label class="form-label" for="profile-max-age"
            >Last seen within (days)</label
          >
          <input
            id="profile-max-age"
            type="number"
            min="1"
            class="form-control"
            v-model.number="rules.max_age_days"
            placeholder="any"
          />
        </div>
        <div class="col-md-4">
          <label class="form-label" for="profile-trust"
            >Minimum source trust</label
          >
          <input
            id="profile-trust"
            type="number"
            min="-100"
            max="100"
            class="form-control"
            v-model.number="rules.min_source_trust"
            placeholder="any"
          />
          <div class="form-text">
            A feed's or server's score modifier; local counts as 0.
          </div>
        </div>
        <div class="col-md-4">
          <div class="form-check form-switch">
            <input
              id="profile-to-ids"
              class="form-check-input"
              type="checkbox"
              v-model="rules.to_ids"
            />
            <label class="form-check-label" for="profile-to-ids"
              >Only flagged for IDS</label
            >
          </div>
        </div>
        <div class="col-md-4">
          <div class="form-check form-switch">
            <input
              id="profile-warninglisted"
              class="form-check-input"
              type="checkbox"
              v-model="rules.exclude_warninglisted"
            />
            <label class="form-check-label" for="profile-warninglisted"
              >Leave out warninglisted</label
            >
          </div>
        </div>
        <div class="col-md-4">
          <div class="form-check form-switch">
            <input
              id="profile-validation"
              class="form-check-input"
              type="checkbox"
              v-model="rules.exclude_validation_issues"
            />
            <label class="form-check-label" for="profile-validation"
              >Leave out validation issues</label
            >
          </div>
        </div>
      </div>

      <h6 class="fw-semibold">Sources</h6>
      <p class="form-text mt-0">
        <em>Only</em> keeps indicators reported by one of them; <em>never</em>
        leaves out those reported only by them (a value a trusted source also
        reports stays).
      </p>
      <table class="table table-sm align-middle mb-3">
        <thead>
          <tr>
            <th>source</th>
            <th class="text-center">only</th>
            <th class="text-center">never</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in known.sources" :key="s.key">
            <td>
              {{ s.name }} <span class="text-muted small">{{ s.kind }}</span>
            </td>
            <td class="text-center">
              <input
                type="checkbox"
                class="form-check-input"
                :aria-label="`Only ${s.name}`"
                :checked="rules.sources.includes(s.key)"
                @change="toggle(rules.sources, s.key)"
              />
            </td>
            <td class="text-center">
              <input
                type="checkbox"
                class="form-check-input"
                :aria-label="`Never ${s.name}`"
                :checked="rules.exclude_sources.includes(s.key)"
                @change="toggle(rules.exclude_sources, s.key)"
              />
            </td>
          </tr>
          <tr v-for="o in known.organisations" :key="`org-${o.id}`">
            <td>
              {{ o.name }} <span class="text-muted small">organisation</span>
            </td>
            <td class="text-center">
              <input
                type="checkbox"
                class="form-check-input"
                :aria-label="`Only ${o.name}`"
                :checked="rules.organisations.includes(o.id)"
                @change="toggle(rules.organisations, o.id)"
              />
            </td>
            <td class="text-center">
              <input
                type="checkbox"
                class="form-check-input"
                :aria-label="`Never ${o.name}`"
                :checked="rules.exclude_organisations.includes(o.id)"
                @change="toggle(rules.exclude_organisations, o.id)"
              />
            </td>
          </tr>
          <tr v-if="!known.sources.length && !known.organisations.length">
            <td colspan="3" class="text-muted">
              No sources with indicators yet.
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="apiError" class="alert alert-danger">{{ apiError }}</div>
      <div class="d-flex justify-content-end gap-2">
        <RouterLink to="/detection-profiles" class="btn btn-outline-secondary"
          >Cancel</RouterLink
        >
        <button class="btn btn-primary" :disabled="!form.name" @click="submit">
          {{ isEdit ? "Save" : "Create profile" }}
        </button>
      </div>
    </div>
  </div>
</template>
