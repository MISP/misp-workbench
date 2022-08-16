<script setup>
import { ATTRIBUTE_CATEGORIES } from "@/helpers/constants";
import { Form, Field } from "vee-validate";
import * as Yup from "yup";

const schema = Yup.object().shape({
  attributeCategory: Yup.string().required("Category is required"),
  attributeType: Yup.string().required("Type is required"),
});
function onSubmit(values, { setErrors }) {
  console.log("add attr");
}
</script>

<template>
  <div class="modal fade" id="addAttributeModal" tabindex="-1" aria-labelledby="addAttributeModalLabel"
    aria-hidden="true">
    <Form @submit="onSubmit" :validation-schema="schema" v-slot="{ errors, isSubmitting }">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" id="addAttributeModalLabel">Add Attribute</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Discard"></button>
          </div>
          <div class="modal-body">
            <div class="row g-3">
              <div class="col text-start">
                <label for="attributeCategory" class="form-label">Category</label>
                <Field id="attributeCategory" name="attributeCategory" v-model="attributeCategory" as="select"
                  class="form-control" :class="{ 'is-invalid': errors.attributeCategory }">
                  <option selected disabled value="">Choose...</option>
                  <option v-for="(category, id) in ATTRIBUTE_CATEGORIES" :value="id">{{ id }}</option>
                </Field>
                <div class="invalid-feedback">{{ errors.attributeCategory }}</div>
              </div>
              <div class="col text-start">
                <label for="attributeType" class="form-label">Type</label>
                <Field id="attributeType" name="attributeType" v-model="attributeType" as="select" class="form-control"
                  :class="{ 'is-invalid': errors.attributeType }">
                  <option selected disabled value="">Choose...</option>
                  <option v-if="attributeCategory"
                    v-for="attributeType in ATTRIBUTE_CATEGORIES[attributeCategory].types" :value="attributeType">
                    {{ attributeType }}</option>
                </Field>
                <div class="invalid-feedback">{{ errors.attributeType }}</div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Discard</button>
            <button type="submit" class="btn btn-primary">Add</button>
          </div>
        </div>
      </div>
    </Form>
  </div>
</template>
