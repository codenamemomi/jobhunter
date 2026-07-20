import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import JobCard from "../components/JobCard";
import EmptyState from "../components/EmptyState";
import { useAuth } from "../store/AuthContext";

const emptyFilters = {
  q: "",
  location: "",
  source: "",
  is_remote: "",
  company: "",
  apply_method: "",
};

export default function Search() {
  const { isAuthenticated } = useAuth();
  const [searchParams] = useSearchParams();
  const [filters, setFilters] = useState(() => ({
    ...emptyFilters,
    apply_method: searchParams.get("apply_method") || "",
  }));
  const [jobs, setJobs] = useState([]);
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [scrapeMsg, setScrapeMsg] = useState("");
  const [scraping, setScraping] = useState(false);
  const [scrapeStatus, setScrapeStatus] = useState(null);
  const [catalog, setCatalog] = useState([]);

  const loadJobs = useCallback(async (f = filters) => {
    setLoading(true);
    setError("");
    try {
      const params = {
        q: f.q || undefined,
        location: f.location || undefined,
        source: f.source || undefined,
        company: f.company || undefined,
        apply_method: f.apply_method || undefined,
        limit: 50,
      };
      if (f.is_remote === "true") params.is_remote = true;
      if (f.is_remote === "false") params.is_remote = false;
      const data = await api.listJobs(params);
      setJobs(data);
    } catch (err) {
      setError(err.message || "Failed to load jobs");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  function refreshScrapeStatus() {
    api.scrapeStatus().then(setScrapeStatus).catch(() => setScrapeStatus(null));
  }

  useEffect(() => {
    api.listSources().then(setSources).catch(() => setSources([]));
    api.sourcesCatalog().then(setCatalog).catch(() => setCatalog([]));
    refreshScrapeStatus();
    const initial = {
      ...emptyFilters,
      apply_method: searchParams.get("apply_method") || "",
    };
    setFilters(initial);
    loadJobs(initial);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function onChange(e) {
    const { name, value } = e.target;
    setFilters((prev) => ({ ...prev, [name]: value }));
  }

  function onSubmit(e) {
    e.preventDefault();
    loadJobs(filters);
  }

  async function scrape() {
    if (!isAuthenticated) {
      setScrapeMsg("Sign in to scrape jobs from external sources.");
      return;
    }
    setScraping(true);
    setScrapeMsg("");
    try {
      const result = await api.scrapeJobs({
        query: filters.q || null,
        sources: filters.source ? [filters.source] : null,
        limit_per_source: 30,
      });
      setScrapeMsg(
        `Fetched ${result.total_fetched} · new ${result.total_new} · email-apply found ${result.email_apply_count ?? 0}`
      );
      if (isAuthenticated) {
        try {
          const bf = await api.backfillApply();
          setScrapeMsg((m) => `${m} · backfilled ${bf.updated} listings`);
        } catch {
          /* optional */
        }
      }
      await loadJobs(filters);
      refreshScrapeStatus();
    } catch (err) {
      setScrapeMsg(err.message || "Scrape failed");
    } finally {
      setScraping(false);
    }
  }

  async function runAutoScrapeNow() {
    if (!isAuthenticated) {
      setScrapeMsg("Sign in to run scheduled scrape.");
      return;
    }
    setScraping(true);
    setScrapeMsg("");
    try {
      const result = await api.runScheduledScrape();
      if (result.status === "error") {
        setScrapeMsg(result.detail || "Scheduled scrape failed");
      } else if (result.status === "busy") {
        setScrapeMsg(result.message || "Scrape already running");
      } else {
        setScrapeMsg(
          `Auto-scrape done · fetched ${result.total_fetched ?? 0} · new ${result.total_new ?? 0}`
        );
      }
      await loadJobs(filters);
      refreshScrapeStatus();
    } catch (err) {
      setScrapeMsg(err.message || "Auto-scrape failed");
    } finally {
      setScraping(false);
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Search jobs</h1>
          <p className="muted">
            Pull listings from multiple boards. Filter by <strong>Email apply</strong> when you want
            mail-in applications.
          </p>
        </div>
        <div className="btn-row toolbar-actions">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={scrape}
            disabled={scraping}
          >
            {scraping ? "Scraping…" : "Scrape now"}
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            onClick={runAutoScrapeNow}
            disabled={scraping}
          >
            Run scheduled scrape
          </button>
        </div>
      </div>

      {scrapeMsg && <div className="alert alert-info">{scrapeMsg}</div>}

      {scrapeStatus && (
        <div className="card scrape-status-card">
          <h2 className="card-title">Auto-scrape</h2>
          <p className="muted small">
            Status:{" "}
            <strong>{scrapeStatus.enabled ? "enabled" : "disabled"}</strong>
            {" · "}every {scrapeStatus.interval_hours}h
            {" · "}
            {scrapeStatus.thread_alive ? "scheduler running" : "scheduler stopped"}
            {scrapeStatus.is_scraping_now ? " · scraping now…" : ""}
          </p>
          <p className="muted small">
            Last run:{" "}
            {scrapeStatus.last_run_at
              ? new Date(scrapeStatus.last_run_at).toLocaleString()
              : "never"}
            {scrapeStatus.next_run_at
              ? ` · next ~ ${new Date(scrapeStatus.next_run_at).toLocaleString()}`
              : ""}
          </p>
          {scrapeStatus.last_error && (
            <p className="alert alert-error" style={{ marginTop: "0.5rem" }}>
              {scrapeStatus.last_error}
            </p>
          )}
          {catalog.length > 0 && (
            <p className="match-signals" style={{ marginTop: "0.6rem" }}>
              <strong>Sources:</strong>{" "}
              {catalog.map((s) => (
                <span key={s.name} className="chip" title={s.requires_key ? "May need API key" : "Free"}>
                  {s.name}
                  {s.requires_key ? " *" : ""}
                </span>
              ))}
            </p>
          )}
          <p className="muted small">
            Configure via <code>AUTO_SCRAPE_*</code> in backend <code>.env</code>, then restart the API.
          </p>
        </div>
      )}

      <form className="filters card" onSubmit={onSubmit}>
        <label className="field">
          <span>Keywords</span>
          <input
            name="q"
            value={filters.q}
            onChange={onChange}
            placeholder="python, react, devops…"
          />
        </label>
        <label className="field">
          <span>Location</span>
          <input
            name="location"
            value={filters.location}
            onChange={onChange}
            placeholder="Remote, Berlin…"
          />
        </label>
        <label className="field">
          <span>Company</span>
          <input
            name="company"
            value={filters.company}
            onChange={onChange}
            placeholder="Acme Inc"
          />
        </label>
        <label className="field">
          <span>Source</span>
          <select name="source" value={filters.source} onChange={onChange}>
            <option value="">All sources</option>
            {sources.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Remote</span>
          <select name="is_remote" value={filters.is_remote} onChange={onChange}>
            <option value="">Any</option>
            <option value="true">Remote only</option>
            <option value="false">On-site / hybrid</option>
          </select>
        </label>
        <label className="field">
          <span>Apply method</span>
          <select name="apply_method" value={filters.apply_method} onChange={onChange}>
            <option value="">Any</option>
            <option value="email">Email apply</option>
            <option value="url">External URL</option>
            <option value="unknown">Unknown</option>
          </select>
        </label>
        <div className="field field-action">
          <span>&nbsp;</span>
          <button type="submit" className="btn btn-primary">
            Search
          </button>
        </div>
      </form>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="page-center">
          <div className="spinner" />
        </div>
      ) : jobs.length === 0 ? (
        <EmptyState
          title="No jobs found"
          hint={
            filters.apply_method === "email"
              ? "Few boards expose emails. Scrape more sources or clear the email filter."
              : isAuthenticated
                ? "Try different filters, or scrape fresh listings."
                : "Sign in and scrape to pull jobs into the database."
          }
          action={
            <button type="button" className="btn btn-primary" onClick={scrape}>
              Scrape now
            </button>
          }
        />
      ) : (
        <>
          <p className="results-count">
            Showing <strong>{jobs.length}</strong> job{jobs.length === 1 ? "" : "s"}
            {filters.apply_method === "email" && " (email apply)"}
          </p>
          <div className="job-list">
            {jobs.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
