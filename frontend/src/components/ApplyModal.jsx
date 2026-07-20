import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";

export default function ApplyModal({ job, matchScore, onClose, onSent }) {
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [draft, setDraft] = useState(null);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [attachCv, setAttachCv] = useState(true);
  // Avoid double create in React Strict Mode / rapid remounts
  const startedForJob = useRef(null);

  useEffect(() => {
    let cancelled = false;
    if (startedForJob.current === job.id && draft) {
      return undefined;
    }
    startedForJob.current = job.id;

    (async () => {
      setLoading(true);
      setError("");
      try {
        const d = await api.createDraft({
          job_id: job.id,
          match_score: matchScore ?? null,
        });
        if (cancelled) return;
        setDraft(d);
        setSubject(d.email_subject || "");
        setBody(d.email_body || "");
      } catch (err) {
        if (!cancelled) setError(err.message || "Could not create draft");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // only re-run when job changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job.id]);

  async function saveAndSend() {
    if (!draft) return;
    setSending(true);
    setError("");
    try {
      await api.updateDraft(draft.id, { subject, body });
      const sent = await api.sendDraft(draft.id, { attach_cv: attachCv });
      onSent?.(sent);
      onClose?.();
    } catch (err) {
      setError(err.message || "Send failed");
    } finally {
      setSending(false);
    }
  }

  async function saveDraftOnly() {
    if (!draft) return;
    setSending(true);
    setError("");
    try {
      const updated = await api.updateDraft(draft.id, { subject, body });
      onSent?.(updated);
      onClose?.();
    } catch (err) {
      setError(err.message || "Save failed");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal-card">
        <div className="modal-header">
          <div>
            <h2>Apply by email</h2>
            <p className="muted small">
              {job.title} · {job.company || "Company"}
            </p>
          </div>
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Close
          </button>
        </div>

        {loading ? (
          <div className="page-center" style={{ minHeight: 120 }}>
            <div className="spinner" />
          </div>
        ) : error && !draft ? (
          <div className="alert alert-error">{error}</div>
        ) : (
          <>
            <label className="field">
              <span>To</span>
              <input value={draft?.email_to || job.apply_email || ""} readOnly />
            </label>
            <label className="field">
              <span>Subject</span>
              <input value={subject} onChange={(e) => setSubject(e.target.value)} />
            </label>
            <label className="field">
              <span>Message</span>
              <textarea rows={10} value={body} onChange={(e) => setBody(e.target.value)} />
            </label>
            <label className="field checkbox-field" style={{ paddingTop: 0 }}>
              <input
                type="checkbox"
                checked={attachCv}
                onChange={(e) => setAttachCv(e.target.checked)}
              />
              <span>Attach your uploaded CV file (original PDF/DOCX)</span>
            </label>

            {error && <div className="alert alert-error">{error}</div>}
            <p className="muted small">
              Attaches the file you uploaded on the CV page when available. Check{" "}
              <strong>Queue → Outbound email</strong> if delivery fails.
            </p>

            <div className="btn-row" style={{ marginTop: "0.75rem" }}>
              <button
                type="button"
                className="btn btn-primary"
                disabled={sending}
                onClick={saveAndSend}
              >
                {sending ? "Working…" : "Send application"}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={sending}
                onClick={saveDraftOnly}
              >
                Save draft only
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
