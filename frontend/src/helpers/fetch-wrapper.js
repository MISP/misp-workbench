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
  return async (url, body) => {
    const authStore = useAuthStore();

    await authStore.ensureValidToken();

    const requestOptions = {
      method,
      headers: authHeader(url),
      url,
    };

    if (body) {
      requestOptions.headers["Content-Type"] = "application/json";
      requestOptions.body = JSON.stringify(body);
    }

    return fetch(url, requestOptions).then((response) =>
      handleResponse(response, requestOptions),
    );
  };
}

function postFormData(url, body) {
  const requestOptions = {
    method: "POST",
    headers: authHeader(url),
    body: body,
  };
  return fetch(url, requestOptions).then((response) =>
    handleResponse(response, requestOptions),
  );
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

async function handleResponse(response, originalRequest) {
  const contentType = response.headers.get("content-type") || "";
  const text = await response.text();

  let data = null;

  const isJson =
    contentType.includes("application/json") || contentType.includes("+json");

  if (isJson && text) {
    try {
      data = JSON.parse(text);
    } catch (e) {
      data = text;
      console.warn("Failed to parse JSON response", e);
    }
  } else {
    data = text;
  }

  if (!response.ok) {
    if (response.status === 401 && originalRequest && !originalRequest._retry) {
      const authStore = useAuthStore();

      originalRequest._retry = true;

      try {
        await authStore.refreshAccessToken();

        // Retry original request with new token
        const newHeaders = {
          ...originalRequest.headers,
          Authorization: `Bearer ${authStore.access_token}`,
        };

        const retryResponse = await fetch(originalRequest.url, {
          ...originalRequest,
          headers: newHeaders,
        });

        return handleResponse(retryResponse); // recursive retry
      } catch (err) {
        await authStore.logout();
        return Promise.reject("Session expired", err);
      }
    }

    const error = (data && data.detail) || response.statusText;
    return Promise.reject(error);
  }

  return data;
}
