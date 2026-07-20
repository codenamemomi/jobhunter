import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import EmptyState from "../components/EmptyState";
import { useAuth } from "../store/AuthContext";

export default function Matches() {
  const { isAuthenticated } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [preferRemote, setPreferRemote] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await api.matchJobs({
        limit: 30,
        min_score: 5,
        prefer_remote: preferRemote ? true : undefined,
      });
      setData(result);
    } catch (err) {
      setData(null);
      setError(err.message || "Could not load matches");
    } finally {
      setLoading(false);
    }
  }, [preferRemote]);

  useEffect(() => {
    if (isAuthenticated) load();
  }, [isAuthenticated, load]);

  async function track(jobId) {
    setBusyId(jobId);
    setMsg("");
    try {
      await api.createApplication({ job_id: jobId, status: "wishlist" });
      setMsg("Added to tracker");
    } catch (err) {
      setMsg(err.message || "Could not track job");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>CV matches</h1>
          <p className="muted">
            Jobs scored against your uploaded CV / skills (rule-based, no AI).
          </p>
        </div>
        <div className="btn-row">
          <label className="field checkbox-field" style={{ paddingTop: 0 }}>
            <input
              type="checkbox"
              checked={preferRemote}
              onChange={(e) => setPreferRemote(e.target.checked)}
            />
            <span>Prefer remote</span>
          </label>
          <button type="button" className="btn btn-secondary" onClick={load} disabled={loading}>
            Refresh
          </button>
          <Link to="/cv" className="btn btn-ghost">
            Edit CV
          </Link>
        </div>
      </div>

      {msg && <div className="alert alert-info">{msg}</div>}
      {error && (
        <div className="alert alert-error">
          {error}{" "}
          <Link to="/cv">Upload or edit your CV</Link>
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
          hint="Upload a CV with clear skills, scrape more jobs, then refresh."
          action={
            <div className="btn-row" style={{ justifyContent: "center" }}>
              <Link to="/cv" className="btn btn-primary">
                Go to CV
              </Link>
              <Link to="/" className="btn btn-ghost">
                Search / scrape jobs
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
          {data.matches.map((m) => (
            <article key={m.job.id} className="card match-card">
              <div className="match-card-top">
                <div>
                  <h3>{m.job.title}</h3>
                  <p className="job-meta">
                    <span>{m.job.company || "Unknown company"}</span>
                    {m.job.location && (
                      <>
                        <span className="dot">·</span>
                        <span>{m.job.location}</span>
                      </>
                    )}
                    {m.job.is_remote && <span className="badge badge-remote">Remote</span>}
                    <span className="badge badge-source">{m.job.source}</span>
                  </p>
                </div>
                <div className="score-ring" title="Match score">
                  <span className="score-value">{Math.round(m.score)}</span>
                  <span className="score-label">match</span>
                </div>
              </div>

              <div className="job-tags">
                {m.matched_skills?.map((s) => (
                  <span key={s} className="chip chip-salary">
                    {s}
                  </span>
                ))}
                {m.matched_titles?.map((t) => (
                  <span key={t} className="chip">
                    {t}
                  </span>
                ))}
              </div>

              <ul className="reason-list">
                {m.reasons?.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>

              <div className="job-actions">
                {m.job.url && (
                  <a className="btn btn-ghost" href={m.job.url} target="_blank" rel="noreferrer">
                    Open listing
                  </a>
                )}
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={busyId === m.job.id}
                  onClick={() => track(m.job.id)}
                >
                  {busyId === m.job.id ? "Saving…" : "Track"}
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
