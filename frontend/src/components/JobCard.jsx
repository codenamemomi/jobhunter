import { useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../store/AuthContext";
import ApplyModal from "./ApplyModal";

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

export default function JobCard({ job, matchScore, onTracked }) {
  const { isAuthenticated } = useAuth();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [showApply, setShowApply] = useState(false);
  const salary = formatSalary(job);
  const tags = (job.tags || "")
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean)
    .slice(0, 6);

  const canEmailApply = job.apply_method === "email" && job.apply_email;

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

  function openApply() {
    if (!isAuthenticated) {
      setMessage("Sign in to apply");
      return;
    }
    setShowApply(true);
  }

  return (
    <>
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
              {canEmailApply && <span className="badge badge-email">Email apply</span>}
              {job.apply_method === "url" && (
                <span className="badge badge-muted">External apply</span>
              )}
            </p>
          </div>
          <div className="job-card-badges">
            {matchScore != null && (
              <span className="badge badge-score">{Math.round(matchScore)}% match</span>
            )}
            <span className="badge badge-source">{job.source}</span>
          </div>
        </div>

        {snippet(job.description) && (
          <p className="job-desc">{snippet(job.description)}</p>
        )}

        <div className="job-tags">
          {salary && <span className="chip chip-salary">{salary}</span>}
          {canEmailApply && (
            <span className="chip chip-email" title={job.apply_email}>
              {job.apply_email}
            </span>
          )}
          {tags.map((tag) => (
            <span key={tag} className="chip">
              {tag}
            </span>
          ))}
        </div>

        <div className="job-actions">
          {(job.apply_url || job.url) && (
            <a
              className="btn btn-ghost"
              href={job.apply_url || job.url}
              target="_blank"
              rel="noreferrer"
            >
              Open listing
            </a>
          )}
          {canEmailApply && (
            <button type="button" className="btn btn-secondary" onClick={openApply}>
              Apply by email
            </button>
          )}
          <button type="button" className="btn btn-primary" onClick={track} disabled={busy}>
            {busy ? "Saving…" : "Track"}
          </button>
          {message && <span className="inline-msg">{message}</span>}
        </div>
      </article>

      {showApply && (
        <ApplyModal
          job={job}
          matchScore={matchScore}
          onClose={() => setShowApply(false)}
          onSent={() => setMessage("Application saved / sent — see Queue")}
        />
      )}
    </>
  );
}
