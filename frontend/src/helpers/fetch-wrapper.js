import { useAuthStore } from "@/stores";
const baseUrl = `${import.meta.env.VITE_API_URL}`;

export const fetchWrapper = {
  get: request("GET"),
  post: request("POST"),
  patch: request("PATCH"),
  put: request("PUT"),
  delete: request("DELETE"),
  authenticate: authenticate(),
  postFormData: postFormData,
};

function request(method) {
  return (url, body) => {
    const requestOptions = {
      method,
      headers: authHeader(url),
    };
    if (body) {
      requestOptions.headers["Content-Type"] = "application/json";
      requestOptions.body = JSON.stringify(body);
    }
    return fetch(url, requestOptions).then(handleResponse);
  };
}

function postFormData(url, body) {
  const requestOptions = {
    method: "POST",
    headers: authHeader(url),
    body: body,
  };
  return fetch(url, requestOptions).then(handleResponse);
}

function authenticate() {
  return (user, password) => {
    return fetch(`${baseUrl}/auth/token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
      },
      body: `username=${user}&password=${password}`,
    }).then(handleResponse);
  };
}

function authHeader(url) {
  const { access_token } = useAuthStore();
  const isLoggedIn = !!access_token;
  const isApiUrl = url.startsWith(import.meta.env.VITE_API_URL);
  if (isLoggedIn && isApiUrl) {
    return { Authorization: `Bearer ${access_token}` };
  } else {
    return {};
  }
}

function handleResponse(response) {
  return response.text().then((text) => {
    const data = text && JSON.parse(text);

    if (!response.ok) {
      const { logout } = useAuthStore();
      if ([401, 403].includes(response.status)) {
        // auto logout if 401 Unauthorized or 403 Forbidden response returned from api
        logout();
      }

      const error = (data && data.detail) || response.statusText;
      return Promise.reject(error);
    }

    return data;
  });
}
