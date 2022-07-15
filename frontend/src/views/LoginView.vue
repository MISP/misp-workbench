<script setup>
import { Form, Field } from "vee-validate";
import * as Yup from "yup";
import { useAuthStore } from "@/stores";
const schema = Yup.object().shape({
  username: Yup.string().required("Username is required"),
  password: Yup.string().required("Password is required"),
});
function onSubmit(values, { setErrors }) {
  const authStore = useAuthStore();
  const { username, password } = values;
  return authStore
    .authenticate(username, password)
    .catch((error) => setErrors({ apiError: error }));
}
</script>

<style>
.form-signin {
  max-width: 330px;
  margin: auto;
  text-align: center;
}

.form-signin .checkbox {
  font-weight: 400;
}

.form-signin .form-floating:focus-within {
  z-index: 2;
}

.form-signin input[type="email"] {
  margin-bottom: -1px;
  border-bottom-right-radius: 0;
  border-bottom-left-radius: 0;
}

.form-signin input[type="password"] {
  margin-bottom: 10px;
  border-top-left-radius: 0;
  border-top-right-radius: 0;
}

.bd-placeholder-img {
  font-size: 1.125rem;
  text-anchor: middle;
  -webkit-user-select: none;
  -moz-user-select: none;
  user-select: none;
}

@media (min-width: 768px) {
  .bd-placeholder-img-lg {
    font-size: 3.5rem;
  }
}
</style>

<template>
  <div id="login-container" class="form-signin d-flex flex-column min-vh-100 justify-content-center align-items-center">
      <Form
        @submit="onSubmit"
        :validation-schema="schema"
        v-slot="{ errors, isSubmitting }"
      >
      <img class="mb-4" src="/public/images/misp-logo-pixel.png" alt="" width="120">

      <div class="form-floating">
          <Field
            id="username"
            name="username"
            type="text"
            class="form-control"
            :class="{ 'is-invalid': errors.username }"
          />
        <label for="username">Email address</label>
        <div class="invalid-feedback">{{ errors.username }}</div>
      </div>

      <div class="form-floating">
          <Field
            name="password"
            type="password"
            class="form-control"
            :class="{ 'is-invalid': errors.password }"
          />
          <label>Password</label>
          <div class="invalid-feedback">{{ errors.password }}</div>
      </div>
      
      <div v-if="errors.apiError" class="w-100 alert alert-danger mt-3 mb-3">
        {{ errors.apiError }}
      </div>

      <button class="w-100 btn btn-lg btn-primary" type="submit">Sign in</button>
      <p class="mt-3 mb-3 text-muted">&copy; 2022</p>
    </Form>
    </div>
</template>
