import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import EmptyState from "../components/EmptyState";
import ApplyModal from "../components/ApplyModal";

export default function Queue() {
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState("draft");
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [editJob, setEditJob] = useState(null);
  const [settingsForm, setSettingsForm] = useState({
    auto_draft_enabled: false,
    auto_send_enabled: false,
    auto_min_score: 75,
    auto_daily_limit: 5,
    auto_prefer_remote: true,
    auto_email_only: true,
  });
  const [emailStatus, setEmailStatus] = useState(null);
  const [testingEmail, setTestingEmail] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [queue, st, es] = await Promise.all([
        api.listApplyQueue(status === "all" ? { status: "all" } : { status }),
        api.getApplySettings(),
        api.emailStatus().catch(() => null),
      ]);
      setItems(queue);
      setSettings(st);
      setEmailStatus(es);
      setSettingsForm({
        auto_draft_enabled: st.auto_draft_enabled,
        auto_send_enabled: st.auto_send_enabled,
        auto_min_score: st.auto_min_score,
        auto_daily_limit: st.auto_daily_limit,
        auto_prefer_remote: st.auto_prefer_remote,
        auto_email_only: st.auto_email_only,
      });
    } catch (err) {
      setError(err.message || "Failed to load queue");
    } finally {
      setLoading(false);
    }
  }, [status]);

  useEffect(() => {
    load();
  }, [load]);

  async function sendOne(id) {
    setBusyId(id);
    setMsg("");
    try {
      await api.sendDraft(id, { attach_cv: true });
      setMsg("Sent (or dry-run if no Brevo key)");
      await load();
    } catch (err) {
      setError(err.message || "Send failed");
    } finally {
      setBusyId(null);
    }
  }

  async function sendAllDrafts() {
    const drafts = items.filter((i) => i.status === "draft");
    if (!drafts.length) return;
    if (!confirm(`Send ${drafts.length} draft application(s)?`)) return;
    setMsg("");
    setError("");
    let ok = 0;
    for (const d of drafts) {
      try {
        await api.sendDraft(d.id, { attach_cv: true });
        ok += 1;
      } catch (err) {
        setError(err.message || "Send failed");
        break;
      }
    }
    setMsg(`Sent ${ok} application(s)`);
    await load();
  }

  async function remove(id) {
    if (!confirm("Remove from tracker/queue?")) return;
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

  async function saveSettings(e) {
    e.preventDefault();
    setMsg("");
    try {
      const st = await api.updateApplySettings(settingsForm);
      setSettings(st);
      setMsg("Auto-apply settings saved");
    } catch (err) {
      setError(err.message || "Could not save settings");
    }
  }

  async function runAuto() {
    setMsg("");
    setError("");
    try {
      const result = await api.runAutoApply();
      setMsg(
        `Auto-run: drafted ${result.drafted}, sent ${result.sent}, skipped ${result.skipped}` +
          (result.errors?.length ? ` · errors: ${result.errors.slice(0, 2).join("; ")}` : "")
      );
      await load();
    } catch (err) {
      setError(err.message || "Auto-run failed");
    }
  }

  async function sendTestEmail() {
    setTestingEmail(true);
    setMsg("");
    setError("");
    try {
      const result = await api.testEmail();
      if (result.ok) {
        setMsg(result.detail);
      } else {
        setError(result.detail);
      }
      const es = await api.emailStatus().catch(() => null);
      setEmailStatus(es);
    } catch (err) {
      setError(err.message || "Test email failed");
    } finally {
      setTestingEmail(false);
    }
  }

  function onSettingsChange(e) {
    const { name, type, checked, value } = e.target;
    setSettingsForm((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : type === "number" ? Number(value) : value,
    }));
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Apply queue</h1>
          <p className="muted">
            Draft and send email applications with your CV. Auto mode only targets email-apply jobs.
          </p>
        </div>
        <div className="btn-row">
          <button type="button" className="btn btn-secondary" onClick={sendAllDrafts}>
            Send all drafts
          </button>
          <button type="button" className="btn btn-ghost" onClick={runAuto}>
            Run auto now
          </button>
        </div>
      </div>

      {msg && <div className="alert alert-info">{msg}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      {emailStatus && (
        <div className="card" style={{ marginBottom: "1.25rem" }}>
          <h2 className="card-title">Outbound email</h2>
          <p className="muted small">
            Provider: <strong>{emailStatus.provider}</strong>
            {" · "}From: <strong>{emailStatus.email_from}</strong>
            {" · "}SMTP password:{" "}
            {emailStatus.smtp_password_set ? "set" : "missing"}
            {" · "}Brevo key: {emailStatus.brevo_key_set ? "set" : "missing"}
          </p>
          <p className="muted small">{emailStatus.hint}</p>
          <div className="btn-row" style={{ marginTop: "0.75rem" }}>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={testingEmail}
              onClick={sendTestEmail}
            >
              {testingEmail ? "Sending…" : "Send test email to me"}
            </button>
          </div>
        </div>
      )}

      <form className="card form-grid" onSubmit={saveSettings}>
        <h2 className="card-title">Auto-apply settings (Phase D)</h2>
        <label className="field checkbox-field">
          <input
            type="checkbox"
            name="auto_draft_enabled"
            checked={settingsForm.auto_draft_enabled}
            onChange={onSettingsChange}
          />
          <span>Auto-create drafts for strong CV matches</span>
        </label>
        <label className="field checkbox-field">
          <input
            type="checkbox"
            name="auto_send_enabled"
            checked={settingsForm.auto_send_enabled}
            onChange={onSettingsChange}
          />
          <span>Auto-send drafts (email-apply only, daily limit)</span>
        </label>
        <label className="field">
          <span>Min match score</span>
          <input
            type="number"
            name="auto_min_score"
            min={0}
            max={100}
            value={settingsForm.auto_min_score}
            onChange={onSettingsChange}
          />
        </label>
        <label className="field">
          <span>Daily send limit</span>
          <input
            type="number"
            name="auto_daily_limit"
            min={0}
            max={50}
            value={settingsForm.auto_daily_limit}
            onChange={onSettingsChange}
          />
        </label>
        <label className="field checkbox-field">
          <input
            type="checkbox"
            name="auto_prefer_remote"
            checked={settingsForm.auto_prefer_remote}
            onChange={onSettingsChange}
          />
          <span>Prefer remote</span>
        </label>
        <label className="field checkbox-field">
          <input
            type="checkbox"
            name="auto_email_only"
            checked={settingsForm.auto_email_only}
            onChange={onSettingsChange}
          />
          <span>Email-apply jobs only</span>
        </label>
        <div className="field field-action">
          <button type="submit" className="btn btn-primary">
            Save settings
          </button>
          {settings && (
            <span className="muted small">Sent today: {settings.sent_today}</span>
          )}
        </div>
        <p className="muted small" style={{ gridColumn: "1 / -1" }}>
          Celery beat runs auto-apply at 08:30 and 18:30 UTC when worker+beat are running. Use
          “Run auto now” anytime. External ATS forms are never auto-filled.
        </p>
      </form>

      <div className="page-header" style={{ marginTop: "0.5rem" }}>
        <label className="field inline-filter">
          <span>Show</span>
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="draft">Drafts</option>
            <option value="applied">Sent / applied</option>
            <option value="wishlist">Wishlist</option>
            <option value="all">All</option>
          </select>
        </label>
        <Link to="/" className="btn btn-ghost">
          Find email-apply jobs
        </Link>
      </div>

      {loading ? (
        <div className="page-center">
          <div className="spinner" />
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          title="Queue is empty"
          hint="Filter Search by “Email apply”, open a job, and click Apply by email — or enable auto-draft."
          action={
            <Link to="/?apply_method=email" className="btn btn-primary">
              Browse email-apply jobs
            </Link>
          }
        />
      ) : (
        <div className="stack">
          {items.map((app) => {
            const job = app.job;
            return (
              <article key={app.id} className="card tracker-card">
                <div className="tracker-top">
                  <div>
                    <h3>{job?.title || `Job #${app.job_id}`}</h3>
                    <p className="job-meta">
                      <span>{job?.company || "Unknown"}</span>
                      <span className="badge badge-source">{app.status}</span>
                      {app.is_auto && <span className="badge badge-muted">auto</span>}
                      {app.match_score != null && (
                        <span className="badge badge-score">{Math.round(app.match_score)}%</span>
                      )}
                    </p>
                    {app.email_to && (
                      <p className="muted small">To: {app.email_to}</p>
                    )}
                  </div>
                </div>
                {app.email_subject && (
                  <p className="small">
                    <strong>Subject:</strong> {app.email_subject}
                  </p>
                )}
                {app.email_body && (
                  <pre className="email-preview">{app.email_body.slice(0, 400)}
                    {app.email_body.length > 400 ? "…" : ""}
                  </pre>
                )}
                <div className="job-actions">
                  {app.status === "draft" && (
                    <>
                      <button
                        type="button"
                        className="btn btn-primary"
                        disabled={busyId === app.id}
                        onClick={() => sendOne(app.id)}
                      >
                        Send
                      </button>
                      {job && (
                        <button
                          type="button"
                          className="btn btn-secondary"
                          onClick={() => setEditJob(job)}
                        >
                          Edit & send
                        </button>
                      )}
                    </>
                  )}
                  {(job?.apply_url || job?.url) && (
                    <a
                      className="btn btn-ghost"
                      href={job.apply_url || job.url}
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
                  {app.sent_at && (
                    <span className="muted small">
                      Sent {new Date(app.sent_at).toLocaleString()}
                    </span>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}

      {editJob && (
        <ApplyModal
          job={editJob}
          onClose={() => setEditJob(null)}
          onSent={() => {
            setEditJob(null);
            load();
          }}
        />
      )}
    </div>
  );
}
