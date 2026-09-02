<script setup>
import { ref, computed, watch } from "vue";
import { storeToRefs } from "pinia";
import { useAnalystDataStore } from "@/stores";
import EventPicker from "@/components/analyst-data/EventPicker.vue";
import RelationshipTypeSelect from "@/components/analyst-data/RelationshipTypeSelect.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faNoteSticky,
  faCommentDots,
  faLink,
} from "@fortawesome/free-solid-svg-icons";

const props = defineProps({
  id: { type: String, required: true },
  modal: Object,
  // the parent this attaches to: an event, attribute, object, or another
  // piece of analyst data when replying
  object_uuid: { type: String, required: true },
  object_type: { type: String, required: true },
  // set when editing; the type is then fixed and the parent is not shown
  existing: { type: Object, default: null },
  initial_type: { type: String, default: "Note" },
});

const emit = defineEmits(["saved"]);

const analystDataStore = useAnalystDataStore();
const { status } = storeToRefs(analystDataStore);

const analystType = ref(props.existing?.analyst_type ?? props.initial_type);

const form = ref(blankForm());

function blankForm() {
  const data = props.existing?.data ?? {};
  return {
    note: data.note ?? "",
    language: data.language ?? "",
    opinion: data.opinion ?? 50,
    comment: data.comment ?? "",
    related_object_uuid: data.related_object_uuid ?? "",
    related_object_type: data.related_object_type ?? "Event",
    relationship_type: data.relationship_type ?? "",
  };
}

// The modal element is created once and reused, so its state is reset when it
// is pointed at a different parent, node or type. Keyed on a string: watching
// an array literal fires on any reactive change and would wipe what the user
// is part way through typing.
const identity = computed(
  () =>
    `${props.object_uuid}|${props.existing?.uuid ?? ""}|${props.initial_type}`,
);

watch(identity, () => {
  analystType.value = props.existing?.analyst_type ?? props.initial_type;
  form.value = blankForm();
  validationError.value = null;
});

const isEdit = computed(() => Boolean(props.existing));

const types = [
  { value: "Note", label: "Note", icon: faNoteSticky },
  { value: "Opinion", label: "Opinion", icon: faCommentDots },
  { value: "Relationship", label: "Relationship", icon: faLink },
];

const validationError = ref(null);

const title = computed(() => {
  if (isEdit.value) return `Edit ${analystType.value}`;

  // The parent type says whether this is a reply or a new top-level entry.
  const replying = ["Note", "Opinion", "Relationship"].includes(
    props.object_type,
  );
  return replying
    ? `Reply with a ${analystType.value}`
    : `Add ${analystType.value} to this ${props.object_type}`;
});

function payloadForType() {
  if (analystType.value === "Note") {
    if (!form.value.note.trim()) return { error: "The note text is required." };
    return {
      payload: {
        note: form.value.note,
        language: form.value.language || null,
      },
    };
  }

  if (analystType.value === "Opinion") {
    if (!form.value.comment.trim())
      return { error: "The opinion comment is required." };
    return {
      payload: {
        opinion: Number(form.value.opinion),
        comment: form.value.comment,
      },
    };
  }

  if (!form.value.relationship_type)
    return { error: "Pick a relationship type." };
  if (!form.value.related_object_uuid)
    return { error: "Pick the event this relates to." };

  return {
    payload: {
      related_object_uuid: form.value.related_object_uuid,
      related_object_type: form.value.related_object_type,
      relationship_type: form.value.relationship_type,
    },
  };
}

const saving = computed(() => status.value.creating || status.value.updating);

async function onSubmit() {
  validationError.value = null;

  const { payload, error } = payloadForType();
  if (error) {
    validationError.value = error;
    return;
  }

  try {
    if (isEdit.value) {
      await analystDataStore.update(props.existing.uuid, payload);
    } else {
      await analystDataStore.create(analystType.value, {
        ...payload,
        object_uuid: props.object_uuid,
        object_type: props.object_type,
      });
    }

    emit("saved");
    props.modal?.hide();
    form.value = blankForm();
  } catch {
    // the store holds the error, which the template renders
  }
}
</script>

<template>
  <div :id="id" class="modal fade" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-lg modal-dialog-centered">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">{{ title }}</h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Discard"
          ></button>
        </div>

        <div class="modal-body">
          <!-- type switch, create only: an existing node keeps its type -->
          <div v-if="!isEdit" class="btn-group mb-3" role="group">
            <button
              v-for="type in types"
              :key="type.value"
              type="button"
              class="btn btn-outline-secondary btn-sm"
              :class="{ active: analystType === type.value }"
              @click="analystType = type.value"
            >
              <FontAwesomeIcon :icon="type.icon" class="me-1" />
              {{ type.label }}
            </button>
          </div>

          <!-- Note -->
          <template v-if="analystType === 'Note'">
            <div class="mb-3">
              <label class="form-label" for="analystNoteText">Note</label>
              <textarea
                id="analystNoteText"
                v-model="form.note"
                class="form-control"
                rows="6"
                placeholder="What should other analysts know?"
              ></textarea>
            </div>
            <div class="mb-3">
              <label class="form-label" for="analystNoteLanguage">
                Language <span class="text-body-secondary">(optional)</span>
              </label>
              <input
                id="analystNoteLanguage"
                v-model="form.language"
                type="text"
                class="form-control"
                placeholder="en"
              />
            </div>
          </template>

          <!-- Opinion -->
          <template v-else-if="analystType === 'Opinion'">
            <div class="mb-3">
              <label class="form-label" for="analystOpinionValue">
                Opinion: <strong>{{ form.opinion }}</strong> / 100
              </label>
              <input
                id="analystOpinionValue"
                v-model="form.opinion"
                type="range"
                class="form-range"
                min="0"
                max="100"
                step="1"
              />
              <div
                class="d-flex justify-content-between small text-body-secondary"
              >
                <span>Strongly disagree</span>
                <span>Neutral</span>
                <span>Strongly agree</span>
              </div>
            </div>
            <div class="mb-3">
              <label class="form-label" for="analystOpinionComment">
                Comment
              </label>
              <textarea
                id="analystOpinionComment"
                v-model="form.comment"
                class="form-control"
                rows="4"
                placeholder="Why do you hold this opinion?"
              ></textarea>
            </div>
          </template>

          <!-- Relationship -->
          <template v-else>
            <div class="mb-3">
              <label class="form-label">Relationship type</label>
              <RelationshipTypeSelect v-model="form.relationship_type" />
            </div>
            <div class="mb-3">
              <label class="form-label">Related event</label>
              <EventPicker v-model="form.related_object_uuid" />
              <div class="form-text">
                Relationships added here point at another event.
              </div>
            </div>
          </template>

          <div v-if="validationError" class="alert alert-warning mb-0">
            {{ validationError }}
          </div>
          <div v-else-if="status.error" class="alert alert-danger mb-0">
            {{ status.error }}
          </div>
        </div>

        <div class="modal-footer">
          <button
            type="button"
            data-bs-dismiss="modal"
            class="btn btn-secondary"
          >
            Discard
          </button>
          <button
            type="submit"
            class="btn btn-primary"
            :class="{ disabled: saving }"
            @click="onSubmit"
          >
            <span
              v-if="saving"
              class="spinner-border spinner-border-sm"
              role="status"
              aria-hidden="true"
            ></span>
            <span v-else>{{ isEdit ? "Save" : "Add" }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
