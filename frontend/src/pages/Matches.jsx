import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import EmptyState from "../components/EmptyState";
import JobCard from "../components/JobCard";
import { useAuth } from "../store/AuthContext";

export default function Matches() {
  const { isAuthenticated } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [preferRemote, setPreferRemote] = useState(true);
  const [emailOnly, setEmailOnly] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await api.matchJobs({
        limit: 30,
        min_score: 5,
        prefer_remote: preferRemote ? true : undefined,
        email_apply_only: emailOnly || undefined,
      });
      setData(result);
    } catch (err) {
      setData(null);
      setError(err.message || "Could not load matches");
    } finally {
      setLoading(false);
    }
  }, [preferRemote, emailOnly]);

  useEffect(() => {
    if (isAuthenticated) load();
  }, [isAuthenticated, load]);

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>CV matches</h1>
          <p className="muted">
            Jobs scored against your CV. Prefer <strong>Email apply</strong> for one-click applications.
          </p>
        </div>
        <div className="btn-row match-toolbar">
          <div className="toolbar-checks">
            <label className="field checkbox-field toolbar-check">
              <input
                type="checkbox"
                checked={preferRemote}
                onChange={(e) => setPreferRemote(e.target.checked)}
              />
              <span>Prefer remote</span>
            </label>
            <label className="field checkbox-field toolbar-check">
              <input
                type="checkbox"
                checked={emailOnly}
                onChange={(e) => setEmailOnly(e.target.checked)}
              />
              <span>Email apply only</span>
            </label>
          </div>
          <div className="toolbar-actions">
            <button type="button" className="btn btn-secondary" onClick={load} disabled={loading}>
              Refresh
            </button>
            <Link to="/queue" className="btn btn-ghost">
              Queue
            </Link>
            <Link to="/cv" className="btn btn-ghost">
              Edit CV
            </Link>
          </div>
        </div>
      </div>

      {error && (
        <div className="alert alert-error">
          {error} <Link to="/cv">Upload or edit your CV</Link>
        </div>
      )}

      {data && (data.profile_skills?.length > 0 || data.profile_titles?.length > 0) && (
        <div className="card match-profile">
          <h2 className="card-title">Your profile signals</h2>
          {data.profile_titles?.length > 0 && (
            <p className="match-signals">
              <strong>Titles:</strong>{" "}
              {data.profile_titles.map((t) => (
                <span key={t} className="chip">
                  {t}
                </span>
              ))}
            </p>
          )}
          {data.profile_skills?.length > 0 && (
            <p className="match-signals">
              <strong>Skills:</strong>{" "}
              {data.profile_skills.map((s) => (
                <span key={s} className="chip">
                  {s}
                </span>
              ))}
            </p>
          )}
        </div>
      )}

      {loading ? (
        <div className="page-center">
          <div className="spinner" />
        </div>
      ) : !data || data.matches?.length === 0 ? (
        <EmptyState
          title="No strong matches yet"
          hint={
            emailOnly
              ? "No email-apply jobs match your CV. Scrape more or turn off the email filter."
              : "Upload a CV with clear skills, scrape more jobs, then refresh."
          }
          action={
            <div className="btn-row" style={{ justifyContent: "center" }}>
              <Link to="/cv" className="btn btn-primary">
                Go to CV
              </Link>
              <Link to="/?apply_method=email" className="btn btn-ghost">
                Email-apply search
              </Link>
            </div>
          }
        />
      ) : (
        <div className="stack">
          <p className="results-count">
            <strong>{data.matches.length}</strong> ranked match
            {data.matches.length === 1 ? "" : "es"}
          </p>
          <div className="job-list">
            {data.matches.map((m) => (
              <JobCard key={m.job.id} job={m.job} matchScore={m.score} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
