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
  downloadAttachment: downloadAttachment,
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

function downloadAttachment(url) {
  const requestOptions = {
    method: "GET",
    headers: authHeader(url),
  };
  return fetch(url, requestOptions);
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
  // Read response body as text first. We only JSON.parse when the
  // Content-Type indicates JSON. For NDJSON or other text types we
  // return the raw text so callers can stream/parse it themselves.
  const contentType = response.headers.get("content-type") || "";
  return response.text().then((text) => {
    let data = null;

    const isJson =
      contentType.includes("application/json") || contentType.includes("+json");

    if (isJson && text) {
      try {
        data = JSON.parse(text);
      } catch (e) {
        // If parsing fails, fall back to raw text
        data = text;
        console.warn("Failed to parse JSON response", e);
      }
    } else {
      // For NDJSON and other textual responses return raw text
      data = text;
    }

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
