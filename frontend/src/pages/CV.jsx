import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, getToken } from "../api/client";

const fields = [
  { name: "full_name", label: "Full name" },
  { name: "headline", label: "Headline", placeholder: "Full-stack engineer" },
  { name: "email", label: "Email", type: "email" },
  { name: "phone", label: "Phone" },
  { name: "location", label: "Location" },
];

const textAreas = [
  { name: "summary", label: "Summary", rows: 3 },
  {
    name: "experience",
    label: "Experience",
    rows: 6,
    placeholder: "Role — Company (dates)\nAchievements…",
  },
  { name: "education", label: "Education", rows: 3 },
  { name: "skills", label: "Skills", rows: 2, placeholder: "Python, React, SQL…" },
  { name: "links", label: "Links", rows: 2, placeholder: "GitHub, LinkedIn, portfolio…" },
];

const blank = {
  full_name: "",
  headline: "",
  email: "",
  phone: "",
  location: "",
  summary: "",
  experience: "",
  education: "",
  skills: "",
  links: "",
};

function applyCv(cv, setForm, setMeta) {
  setForm({
    full_name: cv.full_name || "",
    headline: cv.headline || "",
    email: cv.email || "",
    phone: cv.phone || "",
    location: cv.location || "",
    summary: cv.summary || "",
    experience: cv.experience || "",
    education: cv.education || "",
    skills: cv.skills || "",
    links: cv.links || "",
  });
  setMeta({
    original_filename: cv.original_filename,
    parsed_skills: cv.parsed_skills,
    parsed_titles: cv.parsed_titles,
    parsed_keywords: cv.parsed_keywords,
    parsed_at: cv.parsed_at,
    has_raw_text: cv.has_raw_text,
  });
}

export default function CV() {
  const fileRef = useRef(null);
  const [form, setForm] = useState(blank);
  const [meta, setMeta] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const cv = await api.getCv();
        applyCv(cv, setForm, setMeta);
      } catch (err) {
        setError(err.message || "Failed to load CV");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  function onChange(e) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  async function onSave(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    setMsg("");
    try {
      const cv = await api.updateCv(form);
      applyCv(cv, setForm, setMeta);
      setMsg("CV saved and re-parsed for matching");
    } catch (err) {
      setError(err.message || "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function onUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError("");
    setMsg("");
    try {
      const cv = await api.uploadCv(file);
      applyCv(cv, setForm, setMeta);
      setMsg(
        `Uploaded “${cv.original_filename}”. Detected ${
          (cv.parsed_skills || "").split(",").filter(Boolean).length
        } skill(s).`
      );
    } catch (err) {
      setError(err.message || "Upload failed");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function reparse() {
    setError("");
    setMsg("");
    try {
      const cv = await api.parseCv();
      applyCv(cv, setForm, setMeta);
      setMsg("Re-parsed profile for job matching");
    } catch (err) {
      setError(err.message || "Parse failed");
    }
  }

  async function openExport(kind) {
    const url = kind === "pdf" ? api.getCvPdfUrl() : api.getCvHtmlUrl();
    const token = getToken();
    try {
      const res = await fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Export failed (${res.status})`);
      }
      if (kind === "html") {
        const html = await res.text();
        const w = window.open("", "_blank");
        if (w) {
          w.document.write(html);
          w.document.close();
        }
        return;
      }
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `${(form.full_name || "cv").replace(/\s+/g, "_")}.pdf`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (err) {
      setError(err.message || "Export failed");
    }
  }

  const skillChips = (meta.parsed_skills || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  const titleChips = (meta.parsed_titles || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  if (loading) {
    return (
      <div className="page-center">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Your CV</h1>
          <p className="muted">
            Upload a PDF/DOCX or edit manually — we extract skills and match jobs (no AI).
          </p>
        </div>
        <div className="btn-row">
          <Link to="/matches" className="btn btn-primary">
            Find matches
          </Link>
          <button type="button" className="btn btn-ghost" onClick={() => openExport("html")}>
            Preview HTML
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => openExport("pdf")}>
            Download PDF
          </button>
        </div>
      </div>

      {msg && <div className="alert alert-info">{msg}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      <div className="card upload-card">
        <div className="upload-row">
          <div>
            <h2 className="card-title">Upload CV</h2>
            <p className="muted small">
              PDF, DOCX, or TXT · max 5 MB
              {meta.original_filename && (
                <>
                  {" "}
                  · current file: <strong>{meta.original_filename}</strong>
                </>
              )}
            </p>
          </div>
          <div className="btn-row">
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.docx,.txt,.md,application/pdf"
              hidden
              onChange={onUpload}
            />
            <button
              type="button"
              className="btn btn-secondary"
              disabled={uploading}
              onClick={() => fileRef.current?.click()}
            >
              {uploading ? "Uploading…" : "Choose file"}
            </button>
            <button type="button" className="btn btn-ghost" onClick={reparse}>
              Re-parse
            </button>
          </div>
        </div>

        {(skillChips.length > 0 || titleChips.length > 0) && (
          <div className="parsed-block">
            {titleChips.length > 0 && (
              <p className="match-signals">
                <strong>Detected titles:</strong>{" "}
                {titleChips.map((t) => (
                  <span key={t} className="chip">
                    {t}
                  </span>
                ))}
              </p>
            )}
            {skillChips.length > 0 && (
              <p className="match-signals">
                <strong>Detected skills:</strong>{" "}
                {skillChips.map((s) => (
                  <span key={s} className="chip chip-salary">
                    {s}
                  </span>
                ))}
              </p>
            )}
            {meta.parsed_at && (
              <p className="muted small">
                Last parsed {new Date(meta.parsed_at).toLocaleString()}
                {meta.has_raw_text ? " · text extracted from upload" : ""}
              </p>
            )}
          </div>
        )}
      </div>

      <form className="card form-stack" onSubmit={onSave}>
        <h2 className="card-title">Profile details</h2>
        <div className="form-grid two-col">
          {fields.map((f) => (
            <label key={f.name} className="field">
              <span>{f.label}</span>
              <input
                name={f.name}
                type={f.type || "text"}
                value={form[f.name]}
                onChange={onChange}
                placeholder={f.placeholder}
              />
            </label>
          ))}
        </div>

        {textAreas.map((f) => (
          <label key={f.name} className="field">
            <span>{f.label}</span>
            <textarea
              name={f.name}
              rows={f.rows}
              value={form[f.name]}
              onChange={onChange}
              placeholder={f.placeholder}
            />
          </label>
        ))}

        <div className="btn-row">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Saving…" : "Save CV"}
          </button>
          <Link to="/matches" className="btn btn-ghost">
            View matches →
          </Link>
        </div>
      </form>
    </div>
  );
}
