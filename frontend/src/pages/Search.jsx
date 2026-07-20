import { useCallback, useEffect, useState } from "react";
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
};

export default function Search() {
  const { isAuthenticated } = useAuth();
  const [filters, setFilters] = useState(emptyFilters);
  const [jobs, setJobs] = useState([]);
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [scrapeMsg, setScrapeMsg] = useState("");
  const [scraping, setScraping] = useState(false);

  const loadJobs = useCallback(async (f = filters) => {
    setLoading(true);
    setError("");
    try {
      const params = {
        q: f.q || undefined,
        location: f.location || undefined,
        source: f.source || undefined,
        company: f.company || undefined,
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

  useEffect(() => {
    api.listSources().then(setSources).catch(() => setSources([]));
    loadJobs(emptyFilters);
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
        `Fetched ${result.total_fetched} · new ${result.total_new} · updated ${result.total_updated}`
      );
      await loadJobs(filters);
    } catch (err) {
      setScrapeMsg(err.message || "Scrape failed");
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
            Aggregate listings from RemoteOK, Remotive, ArbeitNow, and Adzuna.
          </p>
        </div>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={scrape}
          disabled={scraping}
        >
          {scraping ? "Scraping…" : "Scrape now"}
        </button>
      </div>

      {scrapeMsg && <div className="alert alert-info">{scrapeMsg}</div>}

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
            isAuthenticated
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
