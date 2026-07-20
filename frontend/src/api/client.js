const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(
  /\/$/,
  ""
);

function getToken() {
  return localStorage.getItem("jh_token");
}

export class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request(path, { method = "GET", body, auth = false, headers = {} } = {}) {
  const opts = {
    method,
    headers: {
      Accept: "application/json",
      ...headers,
    },
  };

  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }

  if (auth) {
    const token = getToken();
    if (token) {
      opts.headers.Authorization = `Bearer ${token}`;
    }
  }

  const res = await fetch(`${API_BASE}${path}`, opts);

  if (res.status === 204) {
    return null;
  }

  const contentType = res.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const data = isJson ? await res.json().catch(() => null) : await res.blob();

  if (!res.ok) {
    const detail =
      data && typeof data === "object" && "detail" in data ? data.detail : null;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg || JSON.stringify(d)).join(", ")
          : `Request failed (${res.status})`;
    throw new ApiError(message, res.status, detail);
  }

  return data;
}

export const api = {
  // Auth
  register: (payload) => request("/api/auth/register", { method: "POST", body: payload }),
  login: (payload) => request("/api/auth/login", { method: "POST", body: payload }),
  me: () => request("/api/auth/me", { auth: true }),

  // Jobs
  listJobs: (params = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
    });
    const q = qs.toString();
    return request(`/api/jobs${q ? `?${q}` : ""}`);
  },
  getJob: (id) => request(`/api/jobs/${id}`),
  listSources: () => request("/api/jobs/sources"),
  scrapeJobs: (payload) =>
    request("/api/jobs/scrape", { method: "POST", body: payload, auth: true }),

  // Saved searches
  listSearches: () => request("/api/searches", { auth: true }),
  createSearch: (payload) =>
    request("/api/searches", { method: "POST", body: payload, auth: true }),
  updateSearch: (id, payload) =>
    request(`/api/searches/${id}`, { method: "PATCH", body: payload, auth: true }),
  deleteSearch: (id) =>
    request(`/api/searches/${id}`, { method: "DELETE", auth: true }),

  // Tracker
  listApplications: (params = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
    });
    const q = qs.toString();
    return request(`/api/tracker${q ? `?${q}` : ""}`, { auth: true });
  },
  createApplication: (payload) =>
    request("/api/tracker", { method: "POST", body: payload, auth: true }),
  updateApplication: (id, payload) =>
    request(`/api/tracker/${id}`, { method: "PATCH", body: payload, auth: true }),
  deleteApplication: (id) =>
    request(`/api/tracker/${id}`, { method: "DELETE", auth: true }),
  listStatuses: () => request("/api/tracker/statuses", { auth: true }),

  // CV
  getCv: () => request("/api/cv", { auth: true }),
  updateCv: (payload) => request("/api/cv", { method: "PUT", body: payload, auth: true }),
  parseCv: () => request("/api/cv/parse", { method: "POST", auth: true }),
  matchJobs: (params = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
    });
    const q = qs.toString();
    return request(`/api/cv/matches${q ? `?${q}` : ""}`, { auth: true });
  },
  uploadCv: async (file) => {
    const token = getToken();
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/api/cv/upload`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: form,
    });
    const data = await res.json().catch(() => null);
    if (!res.ok) {
      const detail = data?.detail;
      const message =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((d) => d.msg || JSON.stringify(d)).join(", ")
            : `Upload failed (${res.status})`;
      throw new ApiError(message, res.status, detail);
    }
    return data;
  },
  getCvHtmlUrl: () => `${API_BASE}/api/cv/html`,
  getCvPdfUrl: () => `${API_BASE}/api/cv/pdf`,

  // Alerts
  runAlerts: () => request("/api/alerts/run", { method: "POST", auth: true }),
  previewMatches: (searchId) =>
    request(`/api/alerts/preview/${searchId}`, { auth: true }),
};

export { API_BASE, getToken };
