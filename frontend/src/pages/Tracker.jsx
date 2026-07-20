import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import EmptyState from "../components/EmptyState";

const STATUS_LABELS = {
  wishlist: "Wishlist",
  applied: "Applied",
  phone_screen: "Phone screen",
  interview: "Interview",
  offer: "Offer",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

export default function Tracker() {
  const [apps, setApps] = useState([]);
  const [statuses, setStatuses] = useState([]);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [list, st] = await Promise.all([
        api.listApplications(filter ? { status: filter } : {}),
        api.listStatuses().catch(() => Object.keys(STATUS_LABELS)),
      ]);
      setApps(list);
      setStatuses(st);
    } catch (err) {
      setError(err.message || "Failed to load tracker");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    load();
  }, [load]);

  async function updateStatus(id, status) {
    setBusyId(id);
    try {
      await api.updateApplication(id, { status });
      await load();
    } catch (err) {
      setError(err.message || "Update failed");
    } finally {
      setBusyId(null);
    }
  }

  async function updateNotes(id, notes) {
    setBusyId(id);
    try {
      await api.updateApplication(id, { notes });
      await load();
    } catch (err) {
      setError(err.message || "Could not save notes");
    } finally {
      setBusyId(null);
    }
  }

  async function remove(id) {
    if (!confirm("Remove this application from your tracker?")) return;
    setBusyId(id);
    try {
      await api.deleteApplication(id);
      await load();
    } catch (err) {
      setError(err.message || "Delete failed");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Application tracker</h1>
          <p className="muted">Move roles through your pipeline from wishlist to offer.</p>
        </div>
        <label className="field inline-filter">
          <span>Status</span>
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="">All</option>
            {statuses.map((s) => (
              <option key={s} value={s}>
                {STATUS_LABELS[s] || s}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="page-center">
          <div className="spinner" />
        </div>
      ) : apps.length === 0 ? (
        <EmptyState
          title="Nothing tracked yet"
          hint="From Search, click Track on a job to add it here."
        />
      ) : (
        <div className="stack">
          {apps.map((app) => {
            const job = app.job;
            return (
              <article key={app.id} className="card tracker-card">
                <div className="tracker-top">
                  <div>
                    <h3>{job?.title || `Job #${app.job_id}`}</h3>
                    <p className="job-meta">
                      <span>{job?.company || "Unknown company"}</span>
                      {job?.source && (
                        <>
                          <span className="dot">·</span>
                          <span className="badge badge-source">{job.source}</span>
                        </>
                      )}
                    </p>
                  </div>
                  <select
                    className="status-select"
                    value={app.status}
                    disabled={busyId === app.id}
                    onChange={(e) => updateStatus(app.id, e.target.value)}
                  >
                    {statuses.map((s) => (
                      <option key={s} value={s}>
                        {STATUS_LABELS[s] || s}
                      </option>
                    ))}
                  </select>
                </div>

                <label className="field">
                  <span>Notes</span>
                  <textarea
                    defaultValue={app.notes || ""}
                    rows={2}
                    placeholder="Interview notes, contacts, links…"
                    onBlur={(e) => {
                      const next = e.target.value;
                      if (next !== (app.notes || "")) {
                        updateNotes(app.id, next);
                      }
                    }}
                  />
                </label>

                <div className="job-actions">
                  {job?.url && (
                    <a
                      className="btn btn-ghost"
                      href={job.url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open listing
                    </a>
                  )}
                  <button
                    type="button"
                    className="btn btn-danger"
                    disabled={busyId === app.id}
                    onClick={() => remove(app.id)}
                  >
                    Remove
                  </button>
                  <span className="muted small">
                    Updated {new Date(app.updated_at).toLocaleString()}
                  </span>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
