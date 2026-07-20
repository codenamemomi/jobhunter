import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import EmptyState from "../components/EmptyState";
import JobCard from "../components/JobCard";

const blank = {
  name: "",
  query: "",
  location: "",
  is_remote: "",
  tags: "",
  source: "",
  alerts_enabled: true,
};

export default function Saved() {
  const [searches, setSearches] = useState([]);
  const [sources, setSources] = useState([]);
  const [form, setForm] = useState(blank);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [preview, setPreview] = useState({ id: null, jobs: [] });
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [list, src] = await Promise.all([api.listSearches(), api.listSources()]);
      setSearches(list);
      setSources(src);
    } catch (err) {
      setError(err.message || "Failed to load saved searches");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function onChange(e) {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  async function onCreate(e) {
    e.preventDefault();
    setMsg("");
    setError("");
    try {
      const payload = {
        name: form.name,
        query: form.query || null,
        location: form.location || null,
        tags: form.tags || null,
        source: form.source || null,
        alerts_enabled: form.alerts_enabled,
        is_remote:
          form.is_remote === "" ? null : form.is_remote === "true",
      };
      await api.createSearch(payload);
      setForm(blank);
      setMsg("Saved search created");
      await load();
    } catch (err) {
      setError(err.message || "Could not create search");
    }
  }

  async function remove(id) {
    if (!confirm("Delete this saved search?")) return;
    setBusyId(id);
    try {
      await api.deleteSearch(id);
      if (preview.id === id) setPreview({ id: null, jobs: [] });
      await load();
    } catch (err) {
      setError(err.message || "Delete failed");
    } finally {
      setBusyId(null);
    }
  }

  async function toggleAlerts(search) {
    setBusyId(search.id);
    try {
      await api.updateSearch(search.id, {
        alerts_enabled: !search.alerts_enabled,
      });
      await load();
    } catch (err) {
      setError(err.message || "Update failed");
    } finally {
      setBusyId(null);
    }
  }

  async function previewMatches(id) {
    setBusyId(id);
    setError("");
    try {
      const jobs = await api.previewMatches(id);
      setPreview({ id, jobs });
    } catch (err) {
      setError(err.message || "Preview failed");
    } finally {
      setBusyId(null);
    }
  }

  async function runAlerts() {
    setMsg("");
    setError("");
    try {
      const result = await api.runAlerts();
      const total = (result.results || []).reduce((n, r) => n + (r.matches || 0), 0);
      setMsg(`Alerts ran · ${total} match(es) across your searches (emails dry-run if no Brevo key)`);
    } catch (err) {
      setError(err.message || "Alert run failed");
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Saved searches</h1>
          <p className="muted">Save filters and get alerted when new jobs match.</p>
        </div>
        <button type="button" className="btn btn-secondary" onClick={runAlerts}>
          Run alerts now
        </button>
      </div>

      {msg && <div className="alert alert-info">{msg}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      <form className="card form-grid" onSubmit={onCreate}>
        <h2 className="card-title">New saved search</h2>
        <label className="field">
          <span>Name *</span>
          <input
            name="name"
            required
            value={form.name}
            onChange={onChange}
            placeholder="Remote Python roles"
          />
        </label>
        <label className="field">
          <span>Keywords</span>
          <input name="query" value={form.query} onChange={onChange} placeholder="python" />
        </label>
        <label className="field">
          <span>Location</span>
          <input
            name="location"
            value={form.location}
            onChange={onChange}
            placeholder="Remote"
          />
        </label>
        <label className="field">
          <span>Tags (comma-separated)</span>
          <input name="tags" value={form.tags} onChange={onChange} placeholder="django, fastapi" />
        </label>
        <label className="field">
          <span>Source</span>
          <select name="source" value={form.source} onChange={onChange}>
            <option value="">Any</option>
            {sources.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Remote</span>
          <select name="is_remote" value={form.is_remote} onChange={onChange}>
            <option value="">Any</option>
            <option value="true">Remote only</option>
            <option value="false">Not remote</option>
          </select>
        </label>
        <label className="field checkbox-field">
          <input
            type="checkbox"
            name="alerts_enabled"
            checked={form.alerts_enabled}
            onChange={onChange}
          />
          <span>Enable email alerts</span>
        </label>
        <div className="field field-action">
          <button type="submit" className="btn btn-primary">
            Save search
          </button>
        </div>
      </form>

      {loading ? (
        <div className="page-center">
          <div className="spinner" />
        </div>
      ) : searches.length === 0 ? (
        <EmptyState
          title="No saved searches yet"
          hint="Create one above to track recurring filters."
        />
      ) : (
        <div className="stack">
          {searches.map((s) => (
            <article key={s.id} className="card search-card">
              <div className="search-card-top">
                <div>
                  <h3>{s.name}</h3>
                  <p className="muted small">
                    {[s.query, s.location, s.source, s.tags]
                      .filter(Boolean)
                      .join(" · ") || "No filters"}
                    {s.is_remote === true && " · remote"}
                    {s.is_remote === false && " · on-site"}
                  </p>
                </div>
                <span className={`badge ${s.alerts_enabled ? "badge-ok" : "badge-muted"}`}>
                  {s.alerts_enabled ? "Alerts on" : "Alerts off"}
                </span>
              </div>
              <div className="job-actions">
                <button
                  type="button"
                  className="btn btn-ghost"
                  disabled={busyId === s.id}
                  onClick={() => previewMatches(s.id)}
                >
                  Preview matches
                </button>
                <button
                  type="button"
                  className="btn btn-ghost"
                  disabled={busyId === s.id}
                  onClick={() => toggleAlerts(s)}
                >
                  {s.alerts_enabled ? "Disable alerts" : "Enable alerts"}
                </button>
                <button
                  type="button"
                  className="btn btn-danger"
                  disabled={busyId === s.id}
                  onClick={() => remove(s.id)}
                >
                  Delete
                </button>
              </div>
              {preview.id === s.id && (
                <div className="preview-block">
                  <p className="results-count">
                    {preview.jobs.length} match{preview.jobs.length === 1 ? "" : "es"}
                  </p>
                  {preview.jobs.length === 0 ? (
                    <p className="muted">No current matches for this search.</p>
                  ) : (
                    <div className="job-list compact">
                      {preview.jobs.map((job) => (
                        <JobCard key={job.id} job={job} />
                      ))}
                    </div>
                  )}
                </div>
              )}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
