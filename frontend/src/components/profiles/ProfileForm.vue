<script setup>
import { reactive, ref, computed, watch } from "vue";
import { storeToRefs } from "pinia";
import { router } from "@/router";
import {
  useAuthStore,
  useDetectionProfilesStore,
  useIndicatorsStore,
  useToastsStore,
} from "@/stores";
import { authHelper } from "@/helpers";
import TagsSelect from "@/components/tags/TagsSelect.vue";
import AttributeTypeMultiSelect from "@/components/enums/AttributeTypeMultiSelect.vue";
import ScoreBadge from "@/components/indicators/ScoreBadge.vue";

// With `profile` the form edits it; without, it creates a new one.
const props = defineProps({ profile: { type: Object, default: null } });

const profilesStore = useDetectionProfilesStore();
const indicatorsStore = useIndicatorsStore();
const toastsStore = useToastsStore();
const { scopes } = storeToRefs(useAuthStore());
// What goes out without a review is for reviewers: auto-approval, the
// approval gate, and turning approval or rejections off (the API refuses
// the rest).
const canReview = computed(() =>
  authHelper.hasScope(scopes.value, "indicators:review"),
);
const wasRequired = !!props.profile?.rules?.require_approval;
const wasExcluded = !!props.profile?.rules?.exclude_rejected;

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
  require_approval: false,
  exclude_rejected: false,
};

const form = reactive({
  name: props.profile?.name ?? "",
  description: props.profile?.description ?? "",
  granularity: props.profile?.granularity ?? "indicators",
  auto_approve: props.profile?.auto_approve ?? false,
});
const RISK_FLAGS = [
  ["popular_domain", "popular domain"],
  ["shared_infrastructure", "shared hosting, CDN or cloud"],
  ["warninglisted", "on another warninglist"],
  ["new_source", "only from a new source"],
  ["low_score", "low score"],
];
const gate = reactive({
  enabled: false,
  max_additions: null,
  max_removals: null,
  hold_on_risk: [],
  spike_factor: null,
  low_score: 40,
  new_source_days: 7,
  ...(props.profile?.gate ?? {}),
});
const blankAsNull = (v) => (v === "" || v === undefined ? null : v);
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

// The rules as edited, opened in Explore as a query.
async function explore() {
  try {
    const { query, snapshot } = await profilesStore.queryFor(payloadRules());
    if (snapshot) {
      toastsStore.push(
        "The query lists the sources present now: ones added later aren't covered by it (they are by the profile).",
        "info",
      );
    }
    router.push({ path: "/explore", query: { q: query, tab: "indicators" } });
  } catch (error) {
    apiError.value = error?.message || String(error);
  }
}

async function submit() {
  apiError.value = null;
  const payload = {
    ...form,
    rules: payloadRules(),
    gate: {
      ...gate,
      max_additions: blankAsNull(gate.max_additions),
      max_removals: blankAsNull(gate.max_removals),
      spike_factor: blankAsNull(gate.spike_factor),
    },
  };
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
          <button
            type="button"
            class="btn btn-link btn-sm p-0 ms-2 align-baseline"
            @click="explore"
          >
            Explore them
          </button>
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

      <h6 class="fw-semibold">Review</h6>
      <p class="form-text mt-0">
        Analysts approve, reject or snooze indicators in the
        <RouterLink to="/indicators/review">review queue</RouterLink>.
      </p>
      <div class="row g-3 mb-3">
        <div class="col-md-4">
          <div class="form-check form-switch">
            <input
              id="profile-require-approval"
              class="form-check-input"
              type="checkbox"
              v-model="rules.require_approval"
              :disabled="form.auto_approve || (!canReview && wasRequired)"
            />
            <label class="form-check-label" for="profile-require-approval"
              >Require approval</label
            >
          </div>
          <div class="form-text">
            Only approved indicators, by an analyst or an auto-approve profile;
            the rest wait in the queue.
          </div>
        </div>
        <div class="col-md-4">
          <div class="form-check form-switch">
            <input
              id="profile-exclude-rejected"
              class="form-check-input"
              type="checkbox"
              :checked="rules.exclude_rejected || rules.require_approval"
              :disabled="rules.require_approval || (!canReview && wasExcluded)"
              @change="rules.exclude_rejected = $event.target.checked"
            />
            <label class="form-check-label" for="profile-exclude-rejected"
              >Leave out rejected</label
            >
          </div>
          <div class="form-text">
            Everything else goes out without waiting for a review.
          </div>
        </div>
        <div class="col-md-4">
          <div class="form-check form-switch">
            <input
              id="profile-auto-approve"
              class="form-check-input"
              type="checkbox"
              v-model="form.auto_approve"
              :disabled="rules.require_approval || !canReview"
            />
            <label class="form-check-label" for="profile-auto-approve"
              >Auto-approve what it selects</label
            >
          </div>
          <div class="form-text">
            A rule of the queue: what this profile selects needs no review (an
            analyst's rejection still holds).
          </div>
        </div>
      </div>

      <h6 class="fw-semibold">Approval gate</h6>
      <p class="form-text mt-0">
        Keeps large or risky changes out of its exports, feeds and sinks keeping
        in step, until someone approves its
        <RouterLink
          v-if="isEdit"
          :to="`/detection-profiles/${profile.id}/changes`"
          >changes</RouterLink
        ><template v-else>changes</template>. Everything else goes out as usual.
      </p>
      <div v-if="!canReview" class="form-text mb-2">
        Changing the gate, auto-approval, or turning approval or rejections off
        needs the <code>indicators:review</code> scope.
      </div>
      <div class="form-check form-switch mb-2">
        <input
          id="profile-gate"
          class="form-check-input"
          type="checkbox"
          v-model="gate.enabled"
          :disabled="!canReview"
        />
        <label class="form-check-label" for="profile-gate"
          >Hold large or risky changes</label
        >
      </div>
      <fieldset v-if="gate.enabled" class="row g-3 mb-3" :disabled="!canReview">
        <div class="col-6 col-md-3">
          <label class="form-label small" for="gate-additions"
            >More additions than</label
          >
          <input
            id="gate-additions"
            class="form-control"
            type="number"
            min="0"
            v-model.number="gate.max_additions"
            placeholder="any number"
          />
        </div>
        <div class="col-6 col-md-3">
          <label class="form-label small" for="gate-removals"
            >More removals than</label
          >
          <input
            id="gate-removals"
            class="form-control"
            type="number"
            min="0"
            v-model.number="gate.max_removals"
            placeholder="any number"
          />
        </div>
        <div class="col-6 col-md-3">
          <label class="form-label small" for="gate-spike"
            >Times the usual additions</label
          >
          <input
            id="gate-spike"
            class="form-control"
            type="number"
            min="1.5"
            step="0.5"
            v-model.number="gate.spike_factor"
            placeholder="no spike check"
          />
        </div>
        <div class="col-6 col-md-3">
          <label class="form-label small" for="gate-low-score"
            >Low score below</label
          >
          <input
            id="gate-low-score"
            class="form-control"
            type="number"
            min="0"
            max="100"
            v-model.number="gate.low_score"
          />
        </div>
        <div class="col-12 col-md-9">
          <div class="form-label small">Any addition flagged</div>
          <div
            v-for="[flag, label] in RISK_FLAGS"
            :key="flag"
            class="form-check form-check-inline"
          >
            <input
              :id="`gate-risk-${flag}`"
              class="form-check-input"
              type="checkbox"
              :checked="gate.hold_on_risk.includes(flag)"
              @change="toggle(gate.hold_on_risk, flag)"
            />
            <label class="form-check-label" :for="`gate-risk-${flag}`">{{
              label
            }}</label>
          </div>
        </div>
        <div class="col-6 col-md-3">
          <label class="form-label small" for="gate-new-source"
            >A source is new for (days)</label
          >
          <input
            id="gate-new-source"
            class="form-control"
            type="number"
            min="1"
            max="365"
            v-model.number="gate.new_source_days"
          />
        </div>
      </fieldset>

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
