import { useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../store/AuthContext";

function formatSalary(job) {
  if (job.salary_min == null && job.salary_max == null) return null;
  const cur = job.currency || "";
  if (job.salary_min != null && job.salary_max != null) {
    return `${cur} ${Math.round(job.salary_min)}–${Math.round(job.salary_max)}`.trim();
  }
  if (job.salary_min != null) return `${cur} ${Math.round(job.salary_min)}+`.trim();
  return `up to ${cur} ${Math.round(job.salary_max)}`.trim();
}

function snippet(text, max = 180) {
  if (!text) return "";
  const plain = text.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  return plain.length > max ? `${plain.slice(0, max)}…` : plain;
}

export default function JobCard({ job, onTracked }) {
  const { isAuthenticated } = useAuth();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const salary = formatSalary(job);
  const tags = (job.tags || "")
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean)
    .slice(0, 6);

  async function track() {
    if (!isAuthenticated) {
      setMessage("Sign in to track jobs");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      await api.createApplication({ job_id: job.id, status: "wishlist" });
      setMessage("Added to tracker");
      onTracked?.(job);
    } catch (err) {
      setMessage(err.message || "Could not track job");
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="job-card">
      <div className="job-card-top">
        <div>
          <h3 className="job-title">{job.title}</h3>
          <p className="job-meta">
            <span>{job.company || "Unknown company"}</span>
            {job.location && (
              <>
                <span className="dot">·</span>
                <span>{job.location}</span>
              </>
            )}
            {job.is_remote && <span className="badge badge-remote">Remote</span>}
          </p>
        </div>
        <span className="badge badge-source">{job.source}</span>
      </div>

      {snippet(job.description) && (
        <p className="job-desc">{snippet(job.description)}</p>
      )}

      <div className="job-tags">
        {salary && <span className="chip chip-salary">{salary}</span>}
        {tags.map((tag) => (
          <span key={tag} className="chip">
            {tag}
          </span>
        ))}
      </div>

      <div className="job-actions">
        {job.url && (
          <a className="btn btn-ghost" href={job.url} target="_blank" rel="noreferrer">
            Open listing
          </a>
        )}
        <button type="button" className="btn btn-primary" onClick={track} disabled={busy}>
          {busy ? "Saving…" : "Track"}
        </button>
        {message && <span className="inline-msg">{message}</span>}
      </div>
    </article>
  );
}
